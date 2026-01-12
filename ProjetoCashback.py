import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
import io

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Sistema de Cashback", page_icon="💰", layout="wide")

# Estilos CSS para deixar mais clean
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    div[data-testid="stMetric"] {
        background-color: #F8F9FA;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #DEE2E6;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 Sistema de Gestão de Cashback")

# --- FUNÇÕES ---
def limpar_texto(texto):
    if not isinstance(texto, str):
        return str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.upper().strip()

def limpar_dinheiro(valor):
    if isinstance(valor, (int, float)):
        return valor
    if isinstance(valor, str):
        valor = valor.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        try:
            return float(valor)
        except:
            return 0.0
    return 0.0

def formatar_telefone(telefone):
    tel = ''.join(filter(str.isdigit, str(telefone)))
    tel = tel.lstrip('0')
    if len(tel) >= 10 and not tel.startswith('55'):
        tel = '55' + tel
    return tel

def carregar_csv_com_busca(uploaded_file, palavras_chave):
    try:
        string_io = io.StringIO(uploaded_file.getvalue().decode("latin1"))
        linhas = string_io.readlines()
        linha_inicio = 0
        separador_detectado = ';'
        
        for i, linha in enumerate(linhas):
            if any(chave in linha for chave in palavras_chave):
                linha_inicio = i
                if linha.count(',') > linha.count(';'):
                    separador_detectado = ','
                break
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, sep=separador_detectado, encoding='latin1', skiprows=linha_inicio)
    except:
        return None

# --- SIDEBAR ---
st.sidebar.header("📂 Arquivos")
arquivo_vendas = st.sidebar.file_uploader("Relatório de Vendas", type=["csv", "txt"])
arquivo_cadastro = st.sidebar.file_uploader("Relatório de Cadastro", type=["csv", "txt"])

# --- LÓGICA PRINCIPAL ---
if arquivo_vendas and arquivo_cadastro:
    
    df_vendas = carregar_csv_com_busca(arquivo_vendas, ["Pagamento", "Total Venda", "Matricula"])
    df_cadastro = carregar_csv_com_busca(arquivo_cadastro, ["CPF", "Data de Nascimento"])

    if df_vendas is not None and df_cadastro is not None:
        try:
            col_usuario = next((c for c in df_vendas.columns if 'Usuário' in c or 'Usuario' in c), None)
            col_nome = next((c for c in df_cadastro.columns if 'Nome' in c), None)
            col_valor = next((c for c in df_vendas.columns if 'Total Venda' in c or 'Venda R$' in c), None)

            if col_usuario and col_nome and col_valor:
                # Tratamento
                df_vendas['chave_match'] = df_vendas[col_usuario].apply(limpar_texto)
                df_vendas['Valor_Limpo'] = df_vendas[col_valor].apply(limpar_dinheiro)
                df_cadastro['chave_match'] = df_cadastro[col_nome].apply(limpar_texto)
                
                if 'Telefone' in df_cadastro.columns:
                    df_cadastro['Telefone_Limpo'] = df_cadastro['Telefone'].apply(formatar_telefone)
                else:
                    df_cadastro['Telefone_Limpo'] = ""

                # Cruzamento
                df_detalhado = pd.merge(df_vendas, df_cadastro, on='chave_match', how='inner')
                df_detalhado['Cashback'] = df_detalhado['Valor_Limpo'] * 0.10
                
                # Agrupamento
                df_final = df_detalhado.groupby([col_nome, 'Telefone_Limpo'], as_index=False)[['Valor_Limpo', 'Cashback']].sum()
                
                # ORDENAÇÃO (Rankeado do maior cashback para o menor)
                df_final = df_final.sort_values(by='Cashback', ascending=False)
                df_final = df_final[df_final['Cashback'] > 0]

                # --- TOP 3 ---
                st.subheader("🏆 Melhores Clientes do Período")
                top_3 = df_final.head(3).reset_index(drop=True)
                if not top_3.empty:
                    c1, c2, c3 = st.columns(3)
                    medals = ["🥇", "🥈", "🥉"]
                    for i, col in enumerate([c1, c2, c3]):
                        if i < len(top_3):
                            col.metric(
                                f"{medals[i]} {top_3.loc[i, col_nome]}",
                                f"R$ {top_3.loc[i, 'Valor_Limpo']:.2f}",
                                f"Cashback: R$ {top_3.loc[i, 'Cashback']:.2f}"
                            )
                
                st.divider()

                # --- LÓGICA DE SELEÇÃO EM MASSA ---
                # Inicializa o estado da tabela se não existir
                if "df_tabela" not in st.session_state:
                    df_final.insert(0, "Enviar?", True)
                    st.session_state.df_tabela = df_final
                else:
                    # Atualiza os valores mantendo a estrutura, caso mude o arquivo
                    if len(df_final) != len(st.session_state.df_tabela):
                        df_final.insert(0, "Enviar?", True)
                        st.session_state.df_tabela = df_final

                # Botões de Ação em Massa
                col_sel, col_desel, col_vazio = st.columns([1, 1, 4])
                
                if col_sel.button("✅ Marcar Todos"):
                    st.session_state.df_tabela["Enviar?"] = True
                    st.rerun()
                
                if col_desel.button("⬜ Desmarcar Todos"):
                    st.session_state.df_tabela["Enviar?"] = False
                    st.rerun()

                st.write("### 👇 Selecione os clientes para envio:")

                # TABELA VISUAL (DATA EDITOR)
                df_editado = st.data_editor(
                    st.session_state.df_tabela,
                    column_config={
                        "Enviar?": st.column_config.CheckboxColumn("Enviar?", width="small"),
                        "Nome": st.column_config.TextColumn("Cliente", width="medium"),
                        "Telefone_Limpo": st.column_config.TextColumn("Telefone", width="medium"),
                        "Valor_Limpo": st.column_config.NumberColumn("Total Gasto", format="R$ %.2f"),
                        "Cashback": st.column_config.ProgressColumn(
                            "Ranking de Cashback",
                            format="R$ %.2f",
                            min_value=0,
                            max_value=float(df_final['Cashback'].max()),
                        ),
                    },
                    disabled=["Nome", "Telefone_Limpo", "Valor_Limpo", "Cashback"],
                    hide_index=True,
                    use_container_width=True,
                    key="editor_dados" # Importante para sincronizar
                )
                
                # Sincroniza a edição manual com o estado
                st.session_state.df_tabela = df_editado
                
                # Filtra os selecionados
                clientes_selecionados = df_editado[df_editado["Enviar?"] == True]

                # --- DISPARO ---
                st.divider()
                st.subheader("🚀 Disparo de Mensagens")
                
                col_pin, col_btn = st.columns([1, 2])
                pin_digitado = col_pin.text_input("Digite o PIN (3040):", type="password", placeholder="****")
                botao_disparo = col_btn.button("GERAR LINKS DE ENVIO", type="primary", use_container_width=True)

                if botao_disparo:
                    if pin_digitado == "3040":
                        st.success(f"Acesso Permitido! Preparando {len(clientes_selecionados)} envios...")
                        st.markdown("---")
                        
                        msg_base = "Olá {nome}, identificamos que você comprou R$ {gasto} conosco recentemente. Por isso, você ganhou R$ {cash} de cashback!"
                        
                        # Grid de cartões para os links
                        for _, row in clientes_selecionados.iterrows():
                            nome = str(row[col_nome]).strip()
                            fone = row['Telefone_Limpo']
                            val_cash = f"{row['Cashback']:.2f}".replace('.', ',')
                            val_gasto = f"{row['Valor_Limpo']:.2f}".replace('.', ',')
                            
                            # PROTEÇÃO CONTRA FALTA DE TELEFONE
                            if not fone or len(fone) < 8:
                                st.warning(f"🚫 {nome}: Telefone não cadastrado ou inválido (Cashback: R$ {val_cash})")
                            else:
                                msg = msg_base.replace("{nome}", nome).replace("{gasto}", val_gasto).replace("{cash}", val_cash)
                                link = f"https://wa.me/{fone}?text={quote(msg)}"
                                
                                # Botão Bonito
                                st.link_button(f"📲 Enviar para {nome} (R$ {val_cash})", link)
                            
                    else:
                        st.error("🚫 PIN Incorreto.")

            else:
                st.error("Colunas essenciais não encontradas.")
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
            # Reseta estado em caso de erro grave
            if "df_tabela" in st.session_state:
                del st.session_state.df_tabela
else:
    st.info("Aguardando upload dos arquivos CSV...")

