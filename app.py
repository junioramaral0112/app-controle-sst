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
    
    /* CSS para posicionar o logo no final da barra lateral */
    [data-testid="stSidebar"] > div:first-child {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }
    .spacer { flex: 1; }
    
    /* CSS PARA O RODAPÉ NA PÁGINA PRINCIPAL */
    .main-footer {
        text-align: center; /* <-- ESTA LINHA CENTRALIZA O TEXTO */
        font-size: 0.8em;
        color: #555;
        border-top: 1px solid #EAEAEA;
        padding-top: 15px;
        margin-top: 50px;
    }
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

# --- FUNÇÃO DO DASHBOARD ---
def verificar_status_empresa(nome_empresa, df_funcionarios, df_aso, df_treinamentos):
    funcionarios_da_empresa = df_funcionarios[df_funcionarios['nome_da_empresa'] == nome_empresa]
    if funcionarios_da_empresa.empty:
        return "Não Liberada", ["Nenhum funcionário cadastrado."]
    
    total_funcionarios = len(funcionarios_da_empresa)
    funcionarios_ok = 0
    pendencias = []
    hoje = datetime.now().date()

    for _, func in funcionarios_da_empresa.iterrows():
        nome_func = func['nome']
        pendencias_funcionario = []
        
        asos_func = df_aso[df_aso['nome_funcionario'] == nome_func]
        if asos_func.empty:
            pendencias_funcionario.append("ASO não encontrado.")
        elif pd.isna(asos_func['validade'].max()) or asos_func['validade'].max() < hoje:
            pendencias_funcionario.append("ASO vencido.")
        
        trein_func = df_treinamentos[df_treinamentos['nome_funcionario'] == nome_func]
        if trein_func.empty:
            pendencias_funcionario.append("Nenhum treinamento encontrado.")
        else:
            treinamentos_validos = trein_func[trein_func['validade'] >= hoje]
            if treinamentos_validos.empty:
                pendencias_funcionario.append("Todos os treinamentos estão vencidos.")

        if not pendencias_funcionario:
            funcionarios_ok += 1
        else:
            pendencias.append(f"**{nome_func}**: " + " | ".join(pendencias_funcionario))

    if funcionarios_ok == total_funcionarios and total_funcionarios > 0:
        return "Aguardando Análise", ["Todos os documentos estão em dia. Aguardando análise manual."]
    else:
        return "Não Liberada", pendencias

# --- 3. LÓGICA DA INTERFACE GRÁFICA (STREAMLIT) ---

dados = {
    'empresas': carregar_dados('empresas'),
    'funcionarios': carregar_dados('funcionarios'),
    'aso': carregar_dados('aso'),
    'treinamentos': carregar_dados('treinamentos'),
    'historico_liberacoes': carregar_dados('historico_liberacoes')
}

st.sidebar.title("SST Controle Terceiros")
menu = st.sidebar.selectbox("Menu de Navegação", [
    "Dashboard de Status", "Análise de Liberação", "Cadastro Único Completo",
    "Cadastro da Empresa", "Cadastro de Funcionário",
    "Registrar ASO", "Registrar Treinamento"
])

if st.sidebar.button("🔄 Recarregar Dados"):
    refresh_data_and_rerun()

st.sidebar.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='padding-top: 200px;'></div>", unsafe_allow_html=True)
st.sidebar.image("sesmt.png", use_container_width=True)
st.sidebar.image("logo_schaefer.png", use_container_width=True)


# --- PÁGINAS DO APLICATIVO ---

if menu == "Dashboard de Status":
    st.title("📊 Dashboard de Status das Empresas")
    st.info("Visão geral da conformidade das empresas. O status registrado manualmente tem prioridade por 24 horas.")

    df_empresas = dados['empresas']
    df_funcionarios = dados['funcionarios']
    df_aso = dados['aso']
    df_treinamentos = dados['treinamentos']
    df_historico = dados['historico_liberacoes']

    if not df_funcionarios.empty and not df_empresas.empty:
        mapa_nomes = df_funcionarios[['id', 'nome']].rename(columns={'id': 'funcionario_id', 'nome': 'nome_funcionario'})
        df_aso = pd.merge(df_aso, mapa_nomes, on='funcionario_id', how='left')
        df_treinamentos = pd.merge(df_treinamentos, mapa_nomes, on='funcionario_id', how='left')
        mapa_empresas = df_empresas[['id', 'nome_da_empresa']].rename(columns={'id': 'empresa_id'})
        df_funcionarios = pd.merge(df_funcionarios, mapa_empresas, on='empresa_id', how='left')

    status_empresas = {"Liberada": [], "Com Pendências": [], "Não Liberada": []}
    hoje = datetime.now().date()

    if not df_empresas.empty:
        for _, empresa_row in df_empresas.iterrows():
            nome_empresa = empresa_row['nome_da_empresa']
            id_empresa = empresa_row['id']
            status_final = ""
            
            historico_empresa = df_historico[df_historico['empresa_id'] == id_empresa].sort_values(by='data_da_acao', ascending=False)
            if not historico_empresa.empty:
                ultima_acao = historico_empresa.iloc[0]
                if pd.notna(ultima_acao['data_da_acao']) and (hoje - ultima_acao['data_da_acao']) < timedelta(hours=24):
                    status_final = ultima_acao['status']

            if not status_final:
                status_auto, _ = verificar_status_empresa(nome_empresa, df_funcionarios, df_aso, df_treinamentos)
                if status_auto == "Aguardando Análise":
                    status_final = "Com Pendências"
                else:
                    status_final = "Não Liberada"
            
            if status_final in status_empresas:
                status_empresas[status_final].append(nome_empresa)
            else:
                status_empresas["Não Liberada"].append(nome_empresa)

    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Empresas Liberadas", len(status_empresas["Liberada"]))
    col2.metric("⚠️ Empresas com Pendências", len(status_empresas["Com Pendências"]))
    col3.metric("❌ Empresas Não Liberadas", len(status_empresas["Não Liberada"]))
    
    with st.expander("Ver Detalhes por Categoria"):
        for status, empresas_lista in status_empresas.items():
            st.subheader(f"{status} ({len(empresas_lista)})")
            if empresas_lista:
                for emp in empresas_lista: st.markdown(f"- {emp}")
            else: st.caption("Nenhuma empresa nesta categoria.")
            st.markdown("---")

elif menu == "Análise de Liberação":
    st.title("🔒 Acesso Restrito - Análise de Liberação")
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated:
        password = st.text_input("Digite a senha para acessar:", type="password")
        if st.button("Entrar"):
            if password == "123456":
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
            funcionarios_da_empresa = dados['funcionarios'][dados['funcionarios']['empresa_id'] == empresa_id_selecionado]
            
            if funcionarios_da_empresa.empty:
                st.warning("Nenhum funcionário cadastrado para esta empresa.")
            else:
                for _, func in funcionarios_da_empresa.iterrows():
                    with st.expander(f"👤 {func['nome']}"):
                        asos_func = dados['aso'][dados['aso']['funcionario_id'] == func['id']]
                        if not asos_func.empty:
                            aso_recente = asos_func.sort_values(by="validade", ascending=False).iloc[0]
                            if pd.notna(aso_recente['url_arquivo']) and aso_recente['url_arquivo'] != 'N/A':
                                st.link_button("Ver/Baixar ASO", aso_recente['url_arquivo'])
                        
                        trein_func = dados['treinamentos'][dados['treinamentos']['funcionario_id'] == func['id']]
                        for _, trein in trein_func.iterrows():
                            if pd.notna(trein['url_arquivo']) and trein['url_arquivo'] != 'N/A':
                                st.link_button(f"Ver/Baixar Certificado: {trein['treinamento']}", trein['url_arquivo'])

elif menu == "Cadastro Único Completo":
    st.header("Cadastro Único Completo")
    with st.form(key="form_unico_completo"):
        with st.expander("1. Dados da Empresa", expanded=True):
            dados_empresa = {"nome_da_empresa": st.text_input("Nome da Empresa*"), "cnpj": st.text_input("CNPJ*")}
        
        with st.expander("2. Dados do Funcionário", expanded=True):
            dados_funcionario = {"nome": st.text_input("Nome do Funcionário*"),"cpf": st.text_input("CPF*"),"funcao": st.text_input("Função"),"data_admissao": st.date_input("Data de Admissão").strftime("%Y-%m-%d")}

        if st.form_submit_button("Salvar Cadastro Completo"):
            if dados_empresa["nome_da_empresa"] and dados_funcionario["nome"]:
                response_empresa = inserir_linha("empresas", dados_empresa)
                if response_empresa and response_empresa.data:
                    empresa_id = response_empresa.data[0]['id']
                    dados_funcionario["empresa_id"] = empresa_id
                    response_func = inserir_linha("funcionarios", dados_funcionario)
                    if response_func and response_func.data:
                        st.success("Empresa e Funcionário salvos com sucesso!")
                        st.balloons()
                        refresh_data_and_rerun()
            else:
                st.warning("Nome da Empresa e Nome do Funcionário são obrigatórios.")

elif menu == "Cadastro da Empresa":
    # ... (código existente, já está completo)
    st.header("Gerenciamento de Empresas")
    with st.form("form_nova_empresa", clear_on_submit=True):
        st.subheader("Adicionar Nova Empresa")
        dados_empresa = {"nome_da_empresa": st.text_input("Nome da Empresa*"),"cnpj": st.text_input("CNPJ*"),"responsavel": st.text_input("Nome do Responsável"),"telefone": st.text_input("Telefone"),"email": st.text_input("E-mail")}
        if st.form_submit_button("Salvar Nova Empresa"):
            if dados_empresa["nome_da_empresa"] and dados_empresa["cnpj"]:
                if inserir_linha("empresas", dados_empresa):
                    st.success(f"Empresa '{dados_empresa['nome_da_empresa']}' cadastrada!")
                    refresh_data_and_rerun()
            else:
                st.warning("Nome e CNPJ são obrigatórios.")

elif menu == "Cadastro de Funcionário":
    # ... (código existente, já está completo)
    st.header("Gerenciamento de Funcionários")
    df_empresas = dados.get('empresas', pd.DataFrame())
    if df_empresas.empty:
        st.warning("É necessário cadastrar uma empresa antes de adicionar um funcionário.")
    else:
        mapa_empresas = pd.Series(df_empresas.id.values, index=df_empresas.nome_da_empresa).to_dict()
        with st.form("form_novo_funcionario", clear_on_submit=True):
            st.subheader("Adicionar Novo Funcionário")
            nome_empresa_selecionada = st.selectbox("Empresa*", options=list(mapa_empresas.keys()))
            dados_funcionario = {"nome": st.text_input("Nome do Funcionário*"),"cpf": st.text_input("CPF*"),"funcao": st.text_input("Função"),"data_admissao": st.date_input("Data de Admissão", value=datetime.today()).strftime("%Y-%m-%d"),"empresa_id": mapa_empresas.get(nome_empresa_selecionada)}
            if st.form_submit_button("Salvar Novo Funcionário"):
                if dados_funcionario["nome"] and dados_funcionario["cpf"] and dados_funcionario["empresa_id"]:
                    if inserir_linha("funcionarios", dados_funcionario):
                        st.success(f"Funcionário '{dados_funcionario['nome']}' cadastrado!")
                        refresh_data_and_rerun()
                else:
                    st.warning("Nome, CPF e Empresa são obrigatórios.")

elif menu == "Registrar ASO":
    # ... (código existente, já está completo)
    st.header("Registro Individual de ASO")
    df_funcionarios = dados.get('funcionarios', pd.DataFrame())
    if df_funcionarios.empty:
        st.warning("Cadastre um funcionário antes de registrar um ASO.")
    else:
        mapa_funcionarios = pd.Series(df_funcionarios.id.values, index=df_funcionarios.nome).to_dict()
        with st.form("form_aso_ind", clear_on_submit=True):
            funcionario_selecionado = st.selectbox("Selecione o Funcionário", options=list(mapa_funcionarios.keys()))
            arquivo = st.file_uploader("Upload do arquivo do ASO")
            dados_aso = {"tipo_aso": st.selectbox("Tipo de ASO", ["Admissional", "Periódico", "Demissional", "Mudança de Função", "Retorno ao Trabalho"]),"data": st.date_input("Data do ASO", value=datetime.today()).strftime("%Y-%m-%d"),"validade": st.date_input("Validade do ASO", value=datetime.today() + timedelta(days=365)).strftime("%Y-%m-%d"),"funcionario_id": mapa_funcionarios.get(funcionario_selecionado)}
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
    # ... (código existente, já está completo)
    st.header("Registro Individual de Treinamento")
    df_funcionarios = dados.get('funcionarios', pd.DataFrame())
    if df_funcionarios.empty:
        st.warning("Cadastre um funcionário antes de registrar um Treinamento.")
    else:
        mapa_funcionarios = pd.Series(df_funcionarios.id.values, index=df_funcionarios.nome).to_dict()
        with st.form("form_train_ind", clear_on_submit=True):
            funcionario_selecionado = st.selectbox("Selecione o Funcionário", options=list(mapa_funcionarios.keys()))
            arquivo = st.file_uploader("Upload do certificado")
            dados_treinamento = {"treinamento": st.text_input("Nome do Treinamento*"),"data": st.date_input("Data do Treinamento", value=datetime.today()).strftime("%Y-%m-%d"),"validade": st.date_input("Validade do Treinamento", value=datetime.today() + timedelta(days=365)).strftime("%Y-%m-%d"),"funcionario_id": mapa_funcionarios.get(funcionario_selecionado)}
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


# --- RODAPÉ NO FINAL DA PÁGINA PRINCIPAL ---
st.markdown(
    """
    <div class='main-footer'>
        Desenvolvido por Dilceu Amaral<br>
        Todos os direitos reservados © 2025
    </div>
    """,
    unsafe_allow_html=True
)