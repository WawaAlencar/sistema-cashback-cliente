import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
import io

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Sistema de Cashback", page_icon="💰", layout="wide")

# Força visualmente o tema claro e ajusta espaçamentos
st.markdown("""
    <style>
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    div[data-testid="stMetric"] {
        background-color: #F0F2F6;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #E0E0E0;
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
            # Identificação de Colunas
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
                df_detalhado['Cashback'] = df_detalhado['Valor_Limpo'] * 0.05
                
                # Agrupamento e Ordenação
                df_final = df_detalhado.groupby([col_nome, 'Telefone_Limpo'], as_index=False)[['Valor_Limpo', 'Cashback']].sum()
                df_final = df_final.sort_values(by='Valor_Limpo', ascending=False) # Ordena por quem gastou mais
                df_final = df_final[df_final['Cashback'] > 0]

                # --- 🏆 ÁREA DE DESTAQUES (TOP CLIENTES) ---
                st.subheader("🏆 Melhores Clientes do Período")
                
                # Pega os 3 primeiros
                top_3 = df_final.head(3).reset_index(drop=True)
                
                if not top_3.empty:
                    col1, col2, col3 = st.columns(3)
                    
                    # Cartão 1 (Ouro)
                    with col1:
                        if len(top_3) >= 1:
                            st.metric(
                                label=f"🥇 1º Lugar: {top_3.loc[0, col_nome]}",
                                value=f"R$ {top_3.loc[0, 'Valor_Limpo']:.2f}",
                                delta=f"Cashback: R$ {top_3.loc[0, 'Cashback']:.2f}"
                            )
                    
                    # Cartão 2 (Prata)
                    with col2:
                        if len(top_3) >= 2:
                            st.metric(
                                label=f"🥈 2º Lugar: {top_3.loc[1, col_nome]}",
                                value=f"R$ {top_3.loc[1, 'Valor_Limpo']:.2f}",
                                delta=f"Cashback: R$ {top_3.loc[1, 'Cashback']:.2f}"
                            )

                    # Cartão 3 (Bronze)
                    with col3:
                        if len(top_3) >= 3:
                            st.metric(
                                label=f"🥉 3º Lugar: {top_3.loc[2, col_nome]}",
                                value=f"R$ {top_3.loc[2, 'Valor_Limpo']:.2f}",
                                delta=f"Cashback: R$ {top_3.loc[2, 'Cashback']:.2f}"
                            )
                st.divider()

                # --- MÉTRICAS GERAIS E TABELA ---
                col_resumo1, col_resumo2 = st.columns(2)
                col_resumo1.info(f"👥 Total de Clientes Identificados: **{len(df_final)}**")
                col_resumo2.success(f"💰 Total de Cashback a Distribuir: **R$ {df_final['Cashback'].sum():.2f}**")

                st.write("### 👇 Selecione os clientes para envio:")
                
                # Tabela Interativa
                df_final.insert(0, "Enviar?", True)
                df_editado = st.data_editor(
                    df_final, 
                    column_config={
                        "Enviar?": st.column_config.CheckboxColumn("Enviar?", default=True),
                        "Valor_Limpo": st.column_config.NumberColumn("Total Comprado", format="R$ %.2f"),
                        "Cashback": st.column_config.NumberColumn("Cashback", format="R$ %.2f"),
                    },
                    disabled=["Nome", "Telefone_Limpo", "Valor_Limpo", "Cashback"],
                    hide_index=True,
                    use_container_width=True
                )

                clientes_selecionados = df_editado[df_editado["Enviar?"] == True]

                # --- ÁREA DE SEGURANÇA E ENVIO ---
                st.divider()
                st.subheader("🚀 Disparo de Mensagens")
                
                col_pin, col_btn = st.columns([1, 2])
                with col_pin:
                    pin_digitado = st.text_input("Digite o PIN (3040):", type="password", placeholder="****")
                
                with col_btn:
                    st.write("") 
                    st.write("") 
                    botao_disparo = st.button("GERAR LINKS DE ENVIO", type="primary", use_container_width=True)

                if botao_disparo:
                    if pin_digitado == "3040":
                        st.success(f"Acesso Permitido! Listando {len(clientes_selecionados)} clientes...")
                        
                        msg_base = "Olá {nome}, identificamos que você comprou R$ {gasto} conosco recentemente. Por isso, você ganhou R$ {cash} de cashback!"
                        
                        st.markdown("---")
                        st.write("#### Clique nos botões para abrir o WhatsApp:")
                        
                        for _, row in clientes_selecionados.iterrows():
                            nome = str(row[col_nome]).strip()
                            fone = row['Telefone_Limpo']
                            # Formatação bonita dos valores
                            val_gasto = f"{row['Valor_Limpo']:.2f}".replace('.', ',')
                            val_cash = f"{row['Cashback']:.2f}".replace('.', ',')
                            
                            msg = msg_base.replace("{nome}", nome).replace("{gasto}", val_gasto).replace("{cash}", val_cash)
                            link = f"https://wa.me/{fone}?text={quote(msg)}"
                            
                            st.link_button(f"📲 {nome} (R$ {val_cash})", link)
                            
                    else:
                        st.error("🚫 PIN Incorreto.")

            else:
                st.error("Erro: Colunas essenciais não encontradas nos arquivos.")
        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")
else:
    st.info("Aguardando upload dos arquivos CSV...")
