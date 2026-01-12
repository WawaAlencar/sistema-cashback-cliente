import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
import io

# Configuração da Página
st.set_page_config(page_title="Sistema de Cashback", layout="wide")

st.title("💰 Sistema de Gestão de Cashback")
st.markdown("Faça o upload dos relatórios para consolidar o saldo dos clientes.")

# --- FUNÇÕES DE LIMPEZA ---
def limpar_texto(texto):
    if not isinstance(texto, str):
        return str(texto) # Garante que números virem texto
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
    # Remove zeros a esquerda se houver erro de formatação
    tel = tel.lstrip('0')
    if len(tel) >= 10 and not tel.startswith('55'):
        tel = '55' + tel
    return tel

# --- FUNÇÃO DE CARREGAMENTO INTELIGENTE ---
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
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return None

# --- INTERFACE ---
st.sidebar.header("📂 Área de Upload")
arquivo_vendas = st.sidebar.file_uploader("Relatório de Vendas", type=["csv", "txt"])
arquivo_cadastro = st.sidebar.file_uploader("Relatório de Cadastro", type=["csv", "txt"])

if arquivo_vendas and arquivo_cadastro:
    
    # Carregamento
    df_vendas = carregar_csv_com_busca(arquivo_vendas, ["Pagamento", "Total Venda", "Matricula"])
    df_cadastro = carregar_csv_com_busca(arquivo_cadastro, ["CPF", "Data de Nascimento"])

    if df_vendas is not None and df_cadastro is not None:
        try:
            # Identificação Automática de Colunas
            col_usuario = next((c for c in df_vendas.columns if 'Usuário' in c or 'Usuario' in c), None)
            col_nome = next((c for c in df_cadastro.columns if 'Nome' in c), None)
            col_valor = next((c for c in df_vendas.columns if 'Total Venda' in c or 'Venda R$' in c), None)

            if not col_usuario or not col_nome or not col_valor:
                st.error("Não identifiquei as colunas Usuário, Nome ou Valor automaticamente.")
            else:
                # Tratamento
                df_vendas['chave_match'] = df_vendas[col_usuario].apply(limpar_texto)
                df_vendas['Valor_Limpo'] = df_vendas[col_valor].apply(limpar_dinheiro)
                
                df_cadastro['chave_match'] = df_cadastro[col_nome].apply(limpar_texto)
                
                if 'Telefone' in df_cadastro.columns:
                    df_cadastro['Telefone_Limpo'] = df_cadastro['Telefone'].apply(formatar_telefone)
                else:
                    df_cadastro['Telefone_Limpo'] = ""

                # 1. Cruzamento (Merge)
                df_detalhado = pd.merge(df_vendas, df_cadastro, on='chave_match', how='inner')

                # 2. Aplicação da Regra (5% de Cashback)
                df_detalhado['Cashback'] = df_detalhado['Valor_Limpo'] * 0.05

                # 3. AGRUPAMENTO (Soma tudo por cliente)
                # Agrupa por Nome e Telefone, somando o Cashback e o Valor Gasto
                df_final = df_detalhado.groupby([col_nome, 'Telefone_Limpo'], as_index=False)[['Valor_Limpo', 'Cashback']].sum()
                
                # Filtrar zerados
                df_final = df_final[df_final['Cashback'] > 0].copy()
                
                # Ordenar por maior cashback
                df_final = df_final.sort_values(by='Cashback', ascending=False)

                # --- EXIBIÇÃO ---
                col1, col2 = st.columns(2)
                col1.metric("Clientes Únicos", len(df_final))
                col2.metric("Cashback Total a Distribuir", f"R$ {df_final['Cashback'].sum():.2f}")

                st.divider()
                st.subheader("📋 Lista Consolidada (Por Cliente)")
                st.dataframe(df_final, use_container_width=True)

                # --- ENVIO ---
                st.subheader("🚀 Central de Envios")
                msg_base = st.text_input("Mensagem", "Olá {nome}, você acumulou R$ {valor} de cashback conosco! Venha aproveitar.")
                
                if st.button("Gerar Links de Envio"):
                    st.write("Clique para enviar:")
                    for _, row in df_final.iterrows():
                        # Proteção: Garante que nome é texto (corrige o erro float)
                        nome = str(row[col_nome]).strip()
                        fone = row['Telefone_Limpo']
                        
                        # Formata o dinheiro (ex: 15.50 vira 15,50)
                        val = f"{row['Cashback']:.2f}".replace('.', ',')
                        
                        # Substituição segura
                        msg = msg_base.replace("{nome}", nome).replace("{valor}", val)
                        
                        link = f"https://wa.me/{fone}?text={quote(msg)}"
                        st.markdown(f"📲 **{nome}**: [Enviar WhatsApp]({link})")

        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")