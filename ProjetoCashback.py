import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
import io
import time

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Sistema de Cashback", page_icon="🔐", layout="wide")

# Estilos CSS (Tema Claro e Ajustes Finais)
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    div[data-testid="stMetric"] {
        background-color: #F8F9FA;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #DEE2E6;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
    }
    .success-box {
        padding: 15px;
        background-color: #D4EDDA;
        color: #155724;
        border-radius: 5px;
        margin-bottom: 10px;
        border: 1px solid #C3E6CB;
    }
    /* Ajuste para botões ficarem mais bonitos */
    div.stButton > button {
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TELA DE LOGIN (BLOQUEIO) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Acesso Restrito")
        st.markdown("Este sistema é privado. Digite a senha para continuar.")
        senha = st.text_input("Senha de Acesso", type="password")
        
        if st.button("Entrar", use_container_width=True):
            if senha == "@Joaozinho20":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    st.stop()

# =========================================================
# DAQUI PARA BAIXO, SÓ CARREGA SE A SENHA ESTIVER CERTA
# =========================================================

st.title("💰 Gestão de Fidelidade (10 por 1)")

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

# --- SIDEBAR E PARÂMETROS ---
with st.sidebar:
    st.header("📂 Arquivos do Sistema")
    arquivo_vendas = st.file_uploader("Relatório de Vendas", type=["csv", "txt"])
    arquivo_cadastro = st.file_uploader("Relatório de Cadastro", type=["csv", "txt"])
    
    st.divider()
    st.header("⚙️ Configuração")
    PRECO_LAVAGEM = st.number_input("Preço da Lavagem (R$)", value=17.90, step=0.50)
    PORCENTAGEM = 0.10 

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
                # Tratamento e Cálculo
                df_vendas['chave_match'] = df_vendas[col_usuario].apply(limpar_texto)
                df_vendas['Valor_Limpo'] = df_vendas[col_valor].apply(limpar_dinheiro)
                df_cadastro['chave_match'] = df_cadastro[col_nome].apply(limpar_texto)
                
                if 'Telefone' in df_cadastro.columns:
                    df_cadastro['Telefone_Limpo'] = df_cadastro['Telefone'].apply(formatar_telefone)
                else:
                    df_cadastro['Telefone_Limpo'] = ""

                df_detalhado = pd.merge(df_vendas, df_cadastro, on='chave_match', how='inner')
                df_detalhado['Cashback'] = df_detalhado['Valor_Limpo'] * PORCENTAGEM
                
                df_final = df_detalhado.groupby([col_nome, 'Telefone_Limpo'], as_index=False)[['Valor_Limpo', 'Cashback']].sum()
                df_final = df_final.sort_values(by='Cashback', ascending=False)
                df_final = df_final[df_final['Cashback'] > 0]
                df_final['Saldo_em_Lavagens'] = df_final['Cashback'] / PRECO_LAVAGEM

                # --- MENSAGEM VISUAL ---
                st.markdown(f"""
                <div class="success-box">
                    <b>🎯 Regra Ativa:</b> A cada <b>10 lavagens</b> (aprox. R$ {PRECO_LAVAGEM*10:.2f}), 
                    o cliente ganha <b>1 Lavagem Grátis</b> (R$ {PRECO_LAVAGEM:.2f}).
                </div>
                """, unsafe_allow_html=True)

                # --- TOP 3 ---
                top_3 = df_final.head(3).reset_index(drop=True)
                if not top_3.empty:
                    st.subheader("🏆 Clientes Mais Próximos do Prêmio")
                    c1, c2, c3 = st.columns(3)
                    medals = ["🥇", "🥈", "🥉"]
                    for i, col in enumerate([c1, c2, c3]):
                        if i < len(top_3):
                            progresso = (top_3.loc[i, 'Cashback'] / PRECO_LAVAGEM) * 100
                            col.metric(
                                f"{medals[i]} {top_3.loc[i, col_nome]}",
                                f"Saldo: R$ {top_3.loc[i, 'Cashback']:.2f}",
                                f"{progresso:.0f}% da meta"
                            )
                
                st.divider()

                # --- INICIALIZAÇÃO DA TABELA ---
                if "df_tabela" not in st.session_state:
                    df_final.insert(0, "Enviar?", True)
                    st.session_state.df_tabela = df_final
                
                if len(df_final) != len(st.session_state.df_tabela):
                     df_final.insert(0, "Enviar?", True)
                     st.session_state.df_tabela = df_final

                # --- BOTÕES DE SELEÇÃO (LADO A LADO) ---
                # Usamos colunas pequenas [1,1,6] para que fiquem colados na esquerda
                col_sel, col_desel, _ = st.columns([1, 1, 6])
                
                with col_sel:
                    if st.button("✅ Marcar Todos", use_container_width=True):
                        st.session_state.df_tabela["Enviar?"] = True
                        st.rerun()
                
                with col_desel:
                    if st.button("⬜ Desmarcar Todos", use_container_width=True):
                        st.session_state.df_tabela["Enviar?"] = False
                        st.rerun()

                st.write("### 👇 Controle de Clientes")

                # --- TABELA ---
                df_editado = st.data_editor(
                    st.session_state.df_tabela,
                    column_config={
                        "Enviar?": st.column_config.CheckboxColumn("Sel.", width="small"),
                        "Nome": st.column_config.TextColumn("Cliente", width="medium"),
                        "Telefone_Limpo": st.column_config.TextColumn("Telefone", width="medium"),
                        "Valor_Limpo": st.column_config.NumberColumn("Gasto Total", format="R$ %.2f"),
                        "Cashback": st.column_config.ProgressColumn(
                            f"Meta: R$ {PRECO_LAVAGEM:.2f}",
                            format="R$ %.2f",
                            min_value=0,
                            max_value=PRECO_LAVAGEM,
                        ),
                        "Saldo_em_Lavagens": st.column_config.NumberColumn("Qtd. Prêmios", format="%.1f 🧺"),
                    },
                    disabled=["Nome", "Telefone_Limpo", "Valor_Limpo", "Cashback", "Saldo_em_Lavagens"],
                    hide_index=True,
                    use_container_width=True,
                    key="editor_dados"
                )
                
                st.session_state.df_tabela = df_editado
                clientes_selecionados = df_editado[df_editado["Enviar?"] == True]

                # --- DISPARO DE MENSAGENS (ALINHADO) ---
                st.divider()
                st.subheader("🚀 Disparo de Mensagens")
                
                # vertical_alignment="bottom" alinha o botão com a caixa de texto, não com o label
                col_pin, col_btn = st.columns([1, 3], vertical_alignment="bottom")
                
                with col_pin:
                    pin_digitado = st.text_input("PIN de Envio:", type="password", placeholder="****")
                
                with col_btn:
                    botao_disparo = st.button("GERAR LINKS DE ENVIO", type="primary", use_container_width=True)

                if botao_disparo:
                    if pin_digitado == "3040":
                        st.success(f"PIN Correto! Listando {len(clientes_selecionados)} envios...")
                        st.markdown("---")
                        
                        msg_base = "Olá {nome}! Você já acumulou R$ {cash} de saldo fidelidade. Isso corresponde a {porc}% de uma lavagem gratuita! Venha completar."
                        msg_premio = "Parabéns {nome}! Você completou o desafio! Você tem R$ {cash} de saldo e já pode resgatar sua LAVAGEM GRÁTIS!"

                        # Grid Responsivo para os Botões
                        cols = st.columns(3) # Exibe em 3 colunas para economizar espaço
                        
                        for index, row in clientes_selecionados.iterrows():
                            nome = str(row[col_nome]).strip()
                            fone = row['Telefone_Limpo']
                            cash_val = row['Cashback']
                            
                            val_cash_str = f"{cash_val:.2f}".replace('.', ',')
                            porcentagem = int((cash_val / PRECO_LAVAGEM) * 100)
                            
                            if cash_val >= PRECO_LAVAGEM:
                                texto_final = msg_premio.replace("{nome}", nome).replace("{cash}", val_cash_str)
                                label_botao = f"🎁 {nome} (RESGATAR!)"
                            else:
                                texto_final = msg_base.replace("{nome}", nome).replace("{cash}", val_cash_str).replace("{porc}", str(porcentagem))
                                label_botao = f"📲 {nome} (Falta {100-porcentagem}%)"

                            # Alterna entre as 3 colunas para exibir os botões
                            with cols[index % 3]:
                                if not fone or len(fone) < 8:
                                    st.warning(f"🚫 {nome} (S/ Tel)")
                                else:
                                    link = f"https://wa.me/{fone}?text={quote(texto_final)}"
                                    st.link_button(label_botao, link, use_container_width=True)
                            
                    else:
                        st.error("🚫 PIN Incorreto.")

            else:
                st.error("Colunas essenciais não encontradas.")
        except Exception as e:
            st.error(f"Erro: {e}")
else:
    st.info("Faça o login e suba os arquivos para começar.")
