import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import numpy as np

# --- 1. CONFIGURAÇÕES GERAIS E CONEXÃO SUPABASE ---
st.set_page_config(layout="wide", page_title="SST Controle Terceiros com Supabase")

# --- ESTILO CSS ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #f0f2f6; }
    [data-testid="stSidebar"] { background-color: #E8F5E9; }
    .stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM O SUPABASE ---
try:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Não foi possível conectar ao Supabase. Verifique suas credenciais em .streamlit/secrets.toml")
    st.stop()

# --- 2. FUNÇÕES DE DADOS (SUPABASE) ---

def refresh_data_and_rerun():
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=30)
def carregar_dados(nome_tabela: str) -> pd.DataFrame:
    response = supabase.table(nome_tabela).select("*").order("id").execute()
    df = pd.DataFrame(response.data)
    for col in ['data', 'validade', 'data_admissao', 'data_da_acao']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    return df

def inserir_linha(nome_tabela: str, dados_dict: dict):
    try:
        return supabase.table(nome_tabela).insert(dados_dict).execute()
    except Exception as e:
        st.error(f"Erro ao inserir dados: {e}")
        return None

def salvar_arquivo_supabase(arquivo, bucket_name: str, file_path: str):
    try:
        supabase.storage.from_(bucket_name).upload(
            file=arquivo.getvalue(),
            path=file_path,
            file_options={"cache-control": "3600", "upsert": "true"}
        )
        return supabase.storage.from_(bucket_name).get_public_url(file_path)
    except Exception as e:
        st.error(f"Erro no upload do arquivo: {e}")
        return None

# --- 3. LÓGICA DA INTERFACE GRÁFICA (STREAMLIT) ---

# Carrega todos os dados do Supabase no início
dados = {
    'empresas': carregar_dados('empresas'),
    'funcionarios': carregar_dados('funcionarios'),
    'aso': carregar_dados('aso'),
    'treinamentos': carregar_dados('treinamentos'),
    'historico_liberacoes': carregar_dados('historico_liberacoes')
}

# Sidebar
st.sidebar.title("SST Control")
menu = st.sidebar.selectbox("Menu de Navegação", [
    "Dashboard de Status", "Análise de Liberação", "Cadastro Único Completo",
    "Cadastro da Empresa", "Cadastro de Funcionário",
    "Registrar ASO", "Registrar Treinamento"
])

if st.sidebar.button("🔄 Recarregar Dados"):
    refresh_data_and_rerun()

# --- PÁGINAS DO APLICATIVO ---

if menu == "Dashboard de Status":
    st.title("📊 Dashboard de Status")
    st.info("Funcionalidade do dashboard em desenvolvimento.")
    # A lógica complexa do dashboard original pode ser re-implementada aqui se necessário.

elif menu == "Análise de Liberação":
    st.title("🔒 Acesso Restrito - Análise de Liberação")
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("Digite a senha para acessar:", type="password")
        if st.button("Entrar"):
            if password == "123456": # Trocar por uma senha segura
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    
    if st.session_state.authenticated:
        st.title("🔍 Análise e Decisão de Liberação")
        df_empresas = dados['empresas']
        mapa_empresas = pd.Series(df_empresas.id.values, index=df_empresas.nome_da_empresa).to_dict()
        nome_empresa_selecionada = st.selectbox("Selecione a Empresa para Análise", options=[""] + list(mapa_empresas.keys()))

        if nome_empresa_selecionada:
            empresa_id_selecionado = mapa_empresas[nome_empresa_selecionada]
            info_empresa = df_empresas[df_empresas['id'] == empresa_id_selecionado].iloc[0]
            
            st.markdown("---")
            st.subheader(f"Resumo da Empresa: {info_empresa['nome_da_empresa']}")
            col1, col2 = st.columns(2)
            col1.markdown(f"**CNPJ:** {info_empresa.get('cnpj', 'N/A')}")
            col2.markdown(f"**Responsável:** {info_empresa.get('responsavel', 'N/A')}")
            st.subheader("Situação dos Funcionários")

            funcionarios_da_empresa = dados['funcionarios'][dados['funcionarios']['empresa_id'] == empresa_id_selecionado]
            hoje = datetime.now().date()

            if funcionarios_da_empresa.empty:
                st.warning("Nenhum funcionário cadastrado para esta empresa.")
            else:
                for _, func in funcionarios_da_empresa.iterrows():
                    with st.expander(f"👤 {func['nome']}"):
                        st.markdown(f"**Função:** {func.get('funcao', 'N/A')}")
                        
                        # ASO
                        asos_func = dados['aso'][dados['aso']['funcionario_id'] == func['id']]
                        if asos_func.empty:
                            st.markdown("- **ASO:** <span style='color:red;'>Não encontrado</span>", unsafe_allow_html=True)
                        else:
                            aso_recente = asos_func.sort_values(by="validade", ascending=False).iloc[0]
                            cor = "green" if pd.notna(aso_recente['validade']) and aso_recente['validade'] >= hoje else "red"
                            st.markdown(f"- **ASO:** <span style='color:{cor};'>Validade: {aso_recente['validade'].strftime('%d/%m/%Y') if pd.notna(aso_recente['validade']) else 'Inválida'}</span>", unsafe_allow_html=True)
                            if pd.notna(aso_recente['url_arquivo']) and aso_recente['url_arquivo'] != 'N/A':
                                st.link_button("Ver ASO", aso_recente['url_arquivo'])

                        # Treinamentos
                        trein_func = dados['treinamentos'][dados['treinamentos']['funcionario_id'] == func['id']]
                        if trein_func.empty:
                            st.markdown("- **Treinamentos:** <span style='color:red;'>Nenhum encontrado</span>", unsafe_allow_html=True)
                        else:
                            for _, trein in trein_func.iterrows():
                                cor = "green" if pd.notna(trein['validade']) and trein['validade'] >= hoje else "red"
                                st.markdown(f"  - **{trein['treinamento']}:** <span style='color:{cor};'>Validade: {trein['validade'].strftime('%d/%m/%Y') if pd.notna(trein['validade']) else 'Inválida'}</span>", unsafe_allow_html=True)
                                if pd.notna(trein['url_arquivo']) and trein['url_arquivo'] != 'N/A':
                                    st.link_button(f"Ver Certificado '{trein['treinamento']}'", trein['url_arquivo'])


elif menu == "Cadastro Único Completo":
    st.header("Cadastro Único Completo")
    st.info("Cadastre empresa, funcionário, ASO e treinamento em um único passo.")

    with st.form(key="form_unico_completo"):
        with st.expander("1. Dados da Empresa", expanded=True):
            dados_empresa = {
                "nome_da_empresa": st.text_input("Nome da Empresa*"),
                "cnpj": st.text_input("CNPJ*")
            }
        
        with st.expander("2. Dados do Funcionário", expanded=True):
            dados_funcionario = {
                "nome": st.text_input("Nome do Funcionário*"),
                "cpf": st.text_input("CPF*"),
                "funcao": st.text_input("Função"),
                "data_admissao": st.date_input("Data de Admissão").strftime("%Y-%m-%d")
            }

        with st.expander("3. Registrar ASO Admissional (Opcional)"):
            registrar_aso = st.checkbox("Registrar ASO")
            aso_arquivo = st.file_uploader("Upload do ASO")
            dados_aso = {
                "tipo_aso": "Admissional",
                "data": st.date_input("Data do ASO").strftime("%Y-%m-%d"),
                "validade": st.date_input("Validade do ASO").strftime("%Y-%m-%d")
            }

        with st.expander("4. Registrar Treinamento Inicial (Opcional)"):
            registrar_treinamento = st.checkbox("Registrar Treinamento")
            trein_arquivo = st.file_uploader("Upload do Certificado de Treinamento")
            dados_treinamento = {
                "treinamento": st.text_input("Nome do Treinamento"),
                "data": st.date_input("Data do Treinamento").strftime("%Y-%m-%d"),
                "validade": st.date_input("Validade do Treinamento").strftime("%Y-%m-%d")
            }

        if st.form_submit_button("Salvar Cadastro Completo"):
            if dados_empresa["nome_da_empresa"] and dados_funcionario["nome"]:
                # Salva a empresa e pega o ID retornado
                response_empresa = inserir_linha("empresas", dados_empresa)
                if response_empresa and response_empresa.data:
                    empresa_id = response_empresa.data[0]['id']
                    st.success(f"Empresa '{dados_empresa['nome_da_empresa']}' salva.")

                    # Salva o funcionário com o ID da empresa
                    dados_funcionario["empresa_id"] = empresa_id
                    response_func = inserir_linha("funcionarios", dados_funcionario)
                    if response_func and response_func.data:
                        funcionario_id = response_func.data[0]['id']
                        st.success(f"Funcionário '{dados_funcionario['nome']}' salvo.")

                        # Salva ASO se marcado
                        if registrar_aso:
                            dados_aso["funcionario_id"] = funcionario_id
                            if aso_arquivo:
                                path = f"aso/{funcionario_id}_{aso_arquivo.name}"
                                dados_aso["url_arquivo"] = salvar_arquivo_supabase(aso_arquivo, "documentos_sst", path)
                            inserir_linha("aso", dados_aso)
                            st.success("ASO salvo.")

                        # Salva Treinamento se marcado
                        if registrar_treinamento and dados_treinamento["treinamento"]:
                            dados_treinamento["funcionario_id"] = funcionario_id
                            if trein_arquivo:
                                path = f"treinamentos/{funcionario_id}_{trein_arquivo.name}"
                                dados_treinamento["url_arquivo"] = salvar_arquivo_supabase(trein_arquivo, "documentos_sst", path)
                            inserir_linha("treinamentos", dados_treinamento)
                            st.success("Treinamento salvo.")
                        
                        st.balloons()
                        refresh_data_and_rerun()
            else:
                st.warning("Nome da Empresa e Nome do Funcionário são obrigatórios.")


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
    df_empresas = dados.get('empresas', pd.DataFrame())
    
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
    df_funcionarios = dados.get('funcionarios', pd.DataFrame())
    if df_funcionarios.empty:
        st.warning("Cadastre um funcionário antes de registrar um ASO.")
    else:
        mapa_funcionarios = pd.Series(df_funcionarios.id.values, index=df_funcionarios.nome).to_dict()
        with st.form("form_aso_ind", clear_on_submit=True):
            funcionario_selecionado = st.selectbox("Selecione o Funcionário", options=list(mapa_funcionarios.keys()))
            arquivo = st.file_uploader("Upload do arquivo do ASO")
            dados_aso = {
                "tipo_aso": st.selectbox("Tipo de ASO", ["Admissional", "Periódico", "Demissional", "Mudança de Função", "Retorno ao Trabalho"]),
                "data": st.date_input("Data do ASO", value=datetime.today()).strftime("%Y-%m-%d"),
                "validade": st.date_input("Validade do ASO", value=datetime.today() + timedelta(days=365)).strftime("%Y-%m-%d"),
                "funcionario_id": mapa_funcionarios.get(funcionario_selecionado)
            }
            if st.form_submit_button("Salvar ASO"):
                if arquivo:
                    path = f"aso/{dados_aso['funcionario_id']}_{arquivo.name}"
                    dados_aso["url_arquivo"] = salvar_arquivo_supabase(arquivo, "documentos_sst", path)
                else:
                    dados_aso["url_arquivo"] = "N/A"
                if inserir_linha("aso", dados_aso):
                    st.success("ASO salvo com sucesso!")
                    refresh_data_and_rerun()

elif menu == "Registrar Treinamento":
    st.header("Registro Individual de Treinamento")
    df_funcionarios = dados.get('funcionarios', pd.DataFrame())
    if df_funcionarios.empty:
        st.warning("Cadastre um funcionário antes de registrar um Treinamento.")
    else:
        mapa_funcionarios = pd.Series(df_funcionarios.id.values, index=df_funcionarios.nome).to_dict()
        with st.form("form_train_ind", clear_on_submit=True):
            funcionario_selecionado = st.selectbox("Selecione o Funcionário", options=list(mapa_funcionarios.keys()))
            arquivo = st.file_uploader("Upload do certificado")
            dados_treinamento = {
                "treinamento": st.text_input("Nome do Treinamento*"),
                "data": st.date_input("Data do Treinamento", value=datetime.today()).strftime("%Y-%m-%d"),
                "validade": st.date_input("Validade do Treinamento", value=datetime.today() + timedelta(days=365)).strftime("%Y-%m-%d"),
                "funcionario_id": mapa_funcionarios.get(funcionario_selecionado)
            }
            if st.form_submit_button("Salvar Treinamento"):
                if dados_treinamento["treinamento"]:
                    if arquivo:
                        path = f"treinamentos/{dados_treinamento['funcionario_id']}_{arquivo.name}"
                        dados_treinamento["url_arquivo"] = salvar_arquivo_supabase(arquivo, "documentos_sst", path)
                    else:
                        dados_treinamento["url_arquivo"] = "N/A"
                    if inserir_linha("treinamentos", dados_treinamento):
                        st.success("Treinamento salvo com sucesso!")
                        refresh_data_and_rerun()
                else:
                    st.warning("O nome do treinamento é obrigatório.")
