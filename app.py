import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import numpy as np

# --- 1. CONFIGURAÇÕES GERAIS E CONEXÃO SUPABASE ---

st.set_page_config(layout="wide", page_title="SST Control com Supabase")

# --- ESTILO CSS ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background-color: #f0f2f6;
    }
    [data-testid="stSidebar"] {
        background-color: #E8F5E9;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM O SUPABASE ---
try:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Não foi possível conectar ao Supabase. Verifique suas credenciais em .streamlit/secrets.toml")
    st.stop()

# --- 2. FUNÇÕES DE DADOS (SUPABASE) ---

def refresh_data_and_rerun():
    """Limpa o cache de dados e reinicia o script para refletir as alterações."""
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=60)
def carregar_dados(nome_tabela: str) -> pd.DataFrame:
    """Carrega dados de qualquer tabela do Supabase."""
    response = supabase.table(nome_tabela).select("*").order("id").execute()
    df = pd.DataFrame(response.data)
    return df

def inserir_linha(nome_tabela: str, dados_dict: dict):
    """Insere uma nova linha em uma tabela."""
    try:
        response = supabase.table(nome_tabela).insert(dados_dict).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao inserir dados em '{nome_tabela}': {e}")
        return False

# --- 3. LÓGICA DA INTERFACE GRÁFICA (STREAMLIT) ---

# Carrega todos os dados necessários no início
tabelas = ["empresas", "funcionarios", "aso", "treinamentos"]
if 'dados' not in st.session_state:
    st.session_state.dados = {}

for tabela in tabelas:
    st.session_state.dados[tabela] = carregar_dados(tabela)


# Sidebar
st.sidebar.title("SST Control (Supabase)")
menu = st.sidebar.selectbox("Menu de Navegação", [
    "Dashboard", "Cadastro da Empresa", "Cadastro de Funcionário", 
    "Registrar ASO", "Registrar Treinamento"
])

if st.sidebar.button("🔄 Recarregar Dados"):
    refresh_data_and_rerun()

# --- PÁGINAS DO APLICATIVO ---

if menu == "Dashboard":
    st.title("📊 Dashboard")
    st.info("Visão geral dos dados cadastrados no banco de dados Supabase.")
    with st.expander("Ver Dados Brutos"):
        for nome_tabela, df in st.session_state.dados.items():
            if not df.empty:
                st.subheader(f"Tabela: {nome_tabela}")
                st.dataframe(df)

elif menu == "Cadastro da Empresa":
    st.header("Gerenciamento de Empresas")
    with st.form("form_nova_empresa", clear_on_submit=True):
        st.subheader("Adicionar Nova Empresa")
        dados_empresa = {
            "nome_da_empresa": st.text_input("Nome da Empresa*"),
            "cnpj": st.text_input("CNPJ*"),
            "responsavel": st.text_input("Nome do Responsável"),
            "telefone": st.text_input("Telefone"),
            "email": st.text_input("E-mail")
        }
        if st.form_submit_button("Salvar Nova Empresa"):
            if dados_empresa["nome_da_empresa"] and dados_empresa["cnpj"]:
                if inserir_linha("empresas", dados_empresa):
                    st.success(f"Empresa '{dados_empresa['nome_da_empresa']}' cadastrada!")
                    refresh_data_and_rerun()
            else:
                st.warning("Nome e CNPJ são obrigatórios.")

elif menu == "Cadastro de Funcionário":
    st.header("Gerenciamento de Funcionários")
    df_empresas = st.session_state.dados.get('empresas', pd.DataFrame())
    
    if df_empresas.empty:
        st.warning("É necessário cadastrar uma empresa antes de adicionar um funcionário.")
    else:
        mapa_empresas = pd.Series(df_empresas.id.values, index=df_empresas.nome_da_empresa).to_dict()

        with st.form("form_novo_funcionario", clear_on_submit=True):
            st.subheader("Adicionar Novo Funcionário")
            nome_empresa_selecionada = st.selectbox("Empresa*", options=list(mapa_empresas.keys()))
            
            dados_funcionario = {
                "nome": st.text_input("Nome do Funcionário*"),
                "cpf": st.text_input("CPF*"),
                "funcao": st.text_input("Função"),
                "data_admissao": st.date_input("Data de Admissão", value=datetime.today()).strftime("%Y-%m-%d"),
                "empresa_id": mapa_empresas.get(nome_empresa_selecionada)
            }

            if st.form_submit_button("Salvar Novo Funcionário"):
                if dados_funcionario["nome"] and dados_funcionario["cpf"] and dados_funcionario["empresa_id"]:
                    if inserir_linha("funcionarios", dados_funcionario):
                        st.success(f"Funcionário '{dados_funcionario['nome']}' cadastrado!")
                        refresh_data_and_rerun()
                else:
                    st.warning("Nome, CPF e Empresa são obrigatórios.")

elif menu == "Registrar ASO":
    st.header("Registro Individual de ASO")
    df_funcionarios = st.session_state.dados.get('funcionarios', pd.DataFrame())
    
    if df_funcionarios.empty:
        st.warning("Cadastre um funcionário antes de registrar um ASO.")
    else:
        mapa_funcionarios = pd.Series(df_funcionarios.id.values, index=df_funcionarios.nome).to_dict()
        with st.form("form_aso_ind", clear_on_submit=True):
            funcionario_selecionado = st.selectbox("Selecione o Funcionário", options=list(mapa_funcionarios.keys()))
            
            dados_aso = {
                "tipo_aso": st.selectbox("Tipo de ASO", ["Admissional", "Periódico", "Demissional", "Mudança de Função", "Retorno ao Trabalho"]),
                "data": st.date_input("Data do ASO", value=datetime.today()).strftime("%Y-%m-%d"),
                "validade": st.date_input("Validade do ASO", value=datetime.today() + timedelta(days=365)).strftime("%Y-%m-%d"),
                "funcionario_id": mapa_funcionarios.get(funcionario_selecionado),
                "url_arquivo": "N/A" # Placeholder, pois não incluímos upload de arquivo nesta versão
            }
            
            if st.form_submit_button("Salvar ASO"):
                if inserir_linha("aso", dados_aso):
                    st.success("ASO salvo com sucesso!")
                    refresh_data_and_rerun()

elif menu == "Registrar Treinamento":
    st.header("Registro Individual de Treinamento")
    df_funcionarios = st.session_state.dados.get('funcionarios', pd.DataFrame())

    if df_funcionarios.empty:
        st.warning("Cadastre um funcionário antes de registrar um Treinamento.")
    else:
        mapa_funcionarios = pd.Series(df_funcionarios.id.values, index=df_funcionarios.nome).to_dict()
        with st.form("form_train_ind", clear_on_submit=True):
            funcionario_selecionado = st.selectbox("Selecione o Funcionário", options=list(mapa_funcionarios.keys()))
            
            dados_treinamento = {
                "treinamento": st.text_input("Nome do Treinamento*"),
                "data": st.date_input("Data do Treinamento", value=datetime.today()).strftime("%Y-%m-%d"),
                "validade": st.date_input("Validade do Treinamento", value=datetime.today() + timedelta(days=365)).strftime("%Y-%m-%d"),
                "funcionario_id": mapa_funcionarios.get(funcionario_selecionado),
                "url_arquivo": "N/A" # Placeholder
            }
            
            if st.form_submit_button("Salvar Treinamento"):
                if dados_treinamento["treinamento"]:
                    if inserir_linha("treinamentos", dados_treinamento):
                        st.success("Treinamento salvo com sucesso!")
                        refresh_data_and_rerun()
                else:
                    st.warning("O nome do treinamento é obrigatório.")