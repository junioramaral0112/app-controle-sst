import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES GERAIS E INICIALIZAÇÃO ---

st.set_page_config(layout="wide", page_title="SST Control")

# --- BLOCO DE ESTILO CSS (FUNDO CINZA) ---

st.markdown(

    """

    <style>

    /* Cor de fundo cinza para a área principal da aplicação */

    [data-testid="stAppViewContainer"] {

        background-color: #f0f2f6;

    }

    /* Cor de fundo da barra lateral */

    [data-testid="stSidebar"] {

        background-color: #E8F5E9;

    }

    /* Organiza a barra lateral para posicionar o logo */

    [data-testid="stSidebar"] > div:first-child {

        display: flex;

        flex-direction: column;

        height: 100vh;

    }

    .spacer { flex: 1; }

    .sidebar-image-container {

        display: flex;

        justify-content: center;

        padding: 20px;

        opacity: 0.2;

    }

    </style>

    """,

    unsafe_allow_html=True

)



# 📁 Constantes de configuração

ARQUIVO_EXCEL = "dados_sst.xlsx"

PASTA_DOCUMENTOS = "documentos_sst"



# 🧩 Função que inicializa o ambiente

def inicializar_ambiente():

    """Verifica e cria o arquivo Excel com todas as abas e a pasta de documentos."""

    if not os.path.exists(ARQUIVO_EXCEL):

        with pd.ExcelWriter(ARQUIVO_EXCEL, engine='openpyxl') as writer:

            pd.DataFrame(columns=["Nome da Empresa", "CNPJ", "Responsável", "Telefone", "E-mail"]).to_excel(writer, sheet_name='Empresas', index=False)

            pd.DataFrame(columns=["Nome", "CPF", "Função", "Empresa", "Data de Admissão"]).to_excel(writer, sheet_name='Funcionários', index=False)

            pd.DataFrame(columns=["Funcionário", "Tipo de ASO", "Data", "Validade", "Arquivo"]).to_excel(writer, sheet_name='ASO', index=False)

            pd.DataFrame(columns=["Funcionário", "Treinamento", "Data", "Validade", "Arquivo"]).to_excel(writer, sheet_name='Treinamentos', index=False)

            pd.DataFrame(columns=["Empresa", "Status", "Observação", "Data da Ação", "Responsável"]).to_excel(writer, sheet_name='Historico_Liberacoes', index=False)

   

    if not os.path.exists(PASTA_DOCUMENTOS):

        os.makedirs(PASTA_DOCUMENTOS)



# --- FUNÇÕES DE LÓGICA E DADOS ---



def salvar_dados_planilha(df_novo, nome_aba):

    """(ANEXAR) Salva novos dados em uma aba específica, lendo e reescrevendo o arquivo."""

    try:

        try:

            sheets_dict = pd.read_excel(ARQUIVO_EXCEL, sheet_name=None, engine='openpyxl')

        except (FileNotFoundError, ValueError):

            sheets_dict = {}



        df_existente = sheets_dict.get(nome_aba, pd.DataFrame())

        df_final = pd.concat([df_existente, df_novo], ignore_index=True)

        sheets_dict[nome_aba] = df_final



        with pd.ExcelWriter(ARQUIVO_EXCEL, engine='openpyxl') as writer:

            for sheet_name, df_sheet in sheets_dict.items():

                df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)

        return True

    except Exception as e:

        st.error(f"Ocorreu um erro CRÍTICO ao salvar os dados: {e}")

        return False



def sobrescrever_abas(sheets_dict_atualizado):

    """(SOBRESCREVER) Salva um dicionário de DataFrames no arquivo Excel, substituindo tudo."""

    try:

        with pd.ExcelWriter(ARQUIVO_EXCEL, engine='openpyxl') as writer:

            for sheet_name, df_sheet in sheets_dict_atualizado.items():

                df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)

        return True

    except Exception as e:

        st.error(f"Ocorreu um erro CRÍTICO ao salvar as alterações: {e}")

        return False



def salvar_arquivo(arquivo_upload, nome_empresa, nome_funcionario, tipo_documento):

    """Salva um arquivo de upload em pastas organizadas."""

    if arquivo_upload:

        try:

            empresa_seguro = "".join(c for c in nome_empresa if c.isalnum() or c in (' ', '_')).rstrip()

            funcionario_seguro = "".join(c for c in nome_funcionario if c.isalnum() or c in (' ', '_')).rstrip()

            caminho_pasta = os.path.join(PASTA_DOCUMENTOS, empresa_seguro, funcionario_seguro)

            os.makedirs(caminho_pasta, exist_ok=True)

            nome_arquivo = f"{tipo_documento.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{arquivo_upload.name.split('.')[-1]}"

            caminho_arquivo = os.path.join(caminho_pasta, nome_arquivo)

            with open(caminho_arquivo, "wb") as f:

                f.write(arquivo_upload.getbuffer())

            return caminho_arquivo

        except Exception as e:

            st.error(f"Erro ao salvar o arquivo '{arquivo_upload.name}': {e}")

    return None



def verificar_status_empresa(nome_empresa, df_funcionarios, df_aso, df_treinamentos):

    """Verifica a situação de uma empresa. Se não estiver 100% OK, retorna 'Não Liberada'."""

    funcionarios_da_empresa = df_funcionarios[df_funcionarios['Empresa'] == nome_empresa]

    if funcionarios_da_empresa.empty:

        return "Não Liberada", ["Nenhum funcionário cadastrado."]

    total_funcionarios = len(funcionarios_da_empresa)

    funcionarios_ok = 0

    pendencias = []

    hoje = datetime.now()

    for _, func in funcionarios_da_empresa.iterrows():

        nome_func = func['Nome']

        pendencias_funcionario = []

        asos_func = df_aso[df_aso['Funcionário'] == nome_func]

        if asos_func.empty:

            pendencias_funcionario.append("ASO não encontrado.")

        else:

            asos_func['Validade'] = pd.to_datetime(asos_func['Validade'], format='%d/%m/%Y', errors='coerce')

            if asos_func.empty or asos_func['Validade'].max() < hoje:

                pendencias_funcionario.append("ASO vencido.")

        trein_func = df_treinamentos[df_treinamentos['Funcionário'] == nome_func]

        if trein_func.empty:

            pendencias_funcionario.append("Nenhum treinamento encontrado.")

        else:

            trein_func['Validade'] = pd.to_datetime(trein_func['Validade'], format='%d/%m/%Y', errors='coerce')

            if not trein_func[trein_func['Validade'] >= hoje].any().any():

                 pendencias_funcionario.append("Todos os treinamentos estão vencidos.")

        if not pendencias_funcionario:

            funcionarios_ok += 1

        else:

            pendencias.append(f"**{nome_func}**: " + " | ".join(pendencias_funcionario))

    if funcionarios_ok == total_funcionarios:

        return "Não Liberada", ["Aguardando análise manual de liberação."]

    else:

        return "Não Liberada", pendencias



# --- INTERFACE GRÁFICA (STREAMLIT) ---



inicializar_ambiente()



st.sidebar.title("SST Control")

menu = st.sidebar.selectbox("Menu de Navegação", [

    "Dashboard de Status", "Análise de Liberação", "Cadastro Único Completo",

    "Cadastro da Empresa", "Cadastro de Funcionário", "Registrar ASO", "Registrar Treinamento"

])



st.sidebar.markdown("<div class='spacer'></div>", unsafe_allow_html=True)

st.sidebar.markdown("<div class='sidebar-image-container'>", unsafe_allow_html=True)

try:

    st.sidebar.image("logo_schaefer.png", width=150)

except Exception:

    st.sidebar.warning("Arquivo 'logo_schaefer.png' não encontrado.")

st.sidebar.markdown("</div>", unsafe_allow_html=True)





if menu == "Dashboard de Status":

    st.title("📊 Dashboard de Status das Empresas")

    st.info("Visão geral da conformidade das empresas. O status registrado manualmente tem prioridade por 24 horas.")

    try:

        sheets_dict = pd.read_excel(ARQUIVO_EXCEL, sheet_name=None)

        df_empresas = sheets_dict.get('Empresas', pd.DataFrame())

        df_funcionarios = sheets_dict.get('Funcionários', pd.DataFrame())

        df_aso = sheets_dict.get('ASO', pd.DataFrame())

        df_treinamentos = sheets_dict.get('Treinamentos', pd.DataFrame())

        df_historico = sheets_dict.get('Historico_Liberacoes', pd.DataFrame())

       

        if not df_historico.empty:

            df_historico['Data da Ação'] = pd.to_datetime(df_historico['Data da Ação'], format='%d/%m/%Y %H:%M:%S', errors='coerce')

       

        status_empresas = {"Liberada": [], "Com Pendências": [], "Não Liberada": []}

        hoje = datetime.now()

       

        if not df_empresas.empty:

            for nome_empresa in df_empresas['Nome da Empresa']:

                status_final = ""

                historico_empresa = df_historico[df_historico['Empresa'] == nome_empresa].sort_values(by='Data da Ação', ascending=False)

                if not historico_empresa.empty:

                    ultima_acao = historico_empresa.iloc[0]

                    if pd.notna(ultima_acao['Data da Ação']) and (hoje - ultima_acao['Data da Ação']) < timedelta(hours=24):

                        status_final = ultima_acao['Status']

                if not status_final:

                    status_final, _ = verificar_status_empresa(nome_empresa, df_funcionarios.copy(), df_aso.copy(), df_treinamentos.copy())

                status_empresas[status_final].append(nome_empresa)



        col1, col2, col3 = st.columns(3)

        col1.metric("✅ Empresas Liberadas", len(status_empresas["Liberada"]))

        col2.metric("⚠️ Empresas com Pendências", len(status_empresas["Com Pendências"]))

        col3.metric("❌ Empresas Não Liberadas", len(status_empresas["Não Liberada"]))

       

        with st.expander("Ver Detalhes por Categoria"):

            for status, empresas in status_empresas.items():

                st.subheader(f"{status} ({len(empresas)})")

                if empresas:

                    for emp in empresas: st.markdown(f"- {emp}")

                else: st.caption("Nenhuma empresa nesta categoria.")

                st.markdown("---")

    except Exception as e:

        st.error(f"Não foi possível carregar o dashboard. Erro: {e}")



elif menu == "Análise de Liberação":

    st.title("🔒 Acesso Restrito - Análise de Liberação")

    if 'authenticated' not in st.session_state: st.session_state.authenticated = False

    if not st.session_state.authenticated:

        password = st.text_input("Digite a senha para acessar:", type="password", key="password_input")

        if st.button("Entrar"):

            if password == "123456":

                st.session_state.authenticated = True

                st.rerun()

            else: st.error("Senha incorreta.")

    if st.session_state.authenticated:

        st.title("🔍 Análise e Decisão de Liberação")

        st.info("Selecione uma empresa para visualizar os dados e documentos antes de registrar o status.")

        try:

            if 'status_para_registrar' not in st.session_state: st.session_state.status_para_registrar = None

            if 'empresa_em_analise' not in st.session_state: st.session_state.empresa_em_analise = None



            empresas_df = pd.read_excel(ARQUIVO_EXCEL, sheet_name='Empresas')

            df_empresas_lista = [""] + empresas_df['Nome da Empresa'].tolist()

            empresa_selecionada = st.selectbox("Selecione a Empresa para Análise", options=df_empresas_lista)

           

            if empresa_selecionada:

                if st.session_state.empresa_em_analise != empresa_selecionada:

                    st.session_state.status_para_registrar = None

                    st.session_state.empresa_em_analise = empresa_selecionada



                info_empresa = empresas_df.query(f"`Nome da Empresa` == '{empresa_selecionada}'").iloc[0]

                funcionarios_da_empresa = pd.read_excel(ARQUIVO_EXCEL, sheet_name='Funcionários').query(f"Empresa == '{empresa_selecionada}'")

                df_aso = pd.read_excel(ARQUIVO_EXCEL, sheet_name='ASO')

                df_treinamentos = pd.read_excel(ARQUIVO_EXCEL, sheet_name='Treinamentos')

                st.markdown("---")

                st.subheader(f"Resumo da Empresa: {info_empresa['Nome da Empresa']}")

                col1, col2 = st.columns(2)

                col1.markdown(f"**CNPJ:** {info_empresa.get('CNPJ', 'N/A')}")

                col2.markdown(f"**Responsável:** {info_empresa.get('Responsável', 'N/A')}")

                st.subheader("Situação dos Funcionários")

                hoje = datetime.now().date()

                if funcionarios_da_empresa.empty: st.warning("Nenhum funcionário cadastrado.")

                else:

                    for _, func in funcionarios_da_empresa.iterrows():

                        with st.expander(f"👤 {func['Nome']}"):

                            st.markdown(f"**Função:** {func.get('Função', 'N/A')}")

                            asos_func = df_aso[df_aso['Funcionário'] == func['Nome']].copy()

                            if asos_func.empty: st.markdown("- **ASO:** <span style='color:red;'>Não encontrado</span>", unsafe_allow_html=True)

                            else:

                                asos_func['Validade'] = pd.to_datetime(asos_func['Validade'], format='%d/%m/%Y', errors='coerce').dt.date

                                aso_recente = asos_func.sort_values(by="Validade", ascending=False).iloc[0]

                                cor = "green" if aso_recente['Validade'] and aso_recente['Validade'] >= hoje else "red"

                                st.markdown(f"- **ASO:** <span style='color:{cor};'>Validade: {aso_recente['Validade'].strftime('%d/%m/%Y') if pd.notna(aso_recente['Validade']) else 'Inválida'}</span>", unsafe_allow_html=True)

                           

                            trein_func = df_treinamentos[df_treinamentos['Funcionário'] == func['Nome']].copy()

                            if trein_func.empty: st.markdown("- **Treinamentos:** <span style='color:red;'>Nenhum encontrado</span>", unsafe_allow_html=True)

                            else:

                                trein_func['Validade'] = pd.to_datetime(trein_func['Validade'], format='%d/%m/%Y', errors='coerce').dt.date

                                idx = trein_func.groupby(['Treinamento'])['Validade'].idxmax()

                                treinamentos_unicos = trein_func.loc[idx]

                                for _, trein in treinamentos_unicos.iterrows():

                                    cor = "green" if trein['Validade'] and trein['Validade'] >= hoje else "red"

                                    st.markdown(f"  - **{trein['Treinamento']}:** <span style='color:{cor};'>Validade: {trein['Validade'].strftime('%d/%m/%Y') if pd.notna(trein['Validade']) else 'Inválida'}</span>", unsafe_allow_html=True)

                           

                            st.markdown("**Documentos Anexados:**")

                            if not asos_func.empty:

                                aso_file_path = aso_recente.get('Arquivo')

                                if pd.notna(aso_file_path) and os.path.exists(aso_file_path):

                                    with open(aso_file_path, "rb") as file:

                                        st.download_button(label=f"Baixar ASO ({os.path.basename(aso_file_path)})", data=file, file_name=os.path.basename(aso_file_path), mime="application/octet-stream", key=f"download_aso_{func.get('CPF', func['Nome'])}")

                                else: st.caption("Arquivo do ASO não encontrado.")

                           

                            if not trein_func.empty:

                                for index, trein in treinamentos_unicos.iterrows():

                                    trein_file_path = trein.get('Arquivo')

                                    if pd.notna(trein_file_path) and os.path.exists(trein_file_path):

                                        with open(trein_file_path, "rb") as file:

                                            st.download_button(label=f"Baixar Certificado: {trein['Treinamento']}", data=file, file_name=os.path.basename(trein_file_path), mime="application/octet-stream", key=f"download_trein_{func.get('CPF', func['Nome'])}_{index}")

                                    else: st.caption(f"Arquivo do treinamento '{trein['Treinamento']}' não encontrado.")

               

                st.markdown("---")

                st.subheader("Ação do Analista")

                col_a, col_b, col_c = st.columns(3)

                if col_a.button("✅ Liberar Empresa"): st.session_state.status_para_registrar = "Liberada"

                if col_b.button("⚠️ Registrar Pendência"): st.session_state.status_para_registrar = "Com Pendências"

                if col_c.button("❌ Não Liberar Empresa"): st.session_state.status_para_registrar = "Não Liberada"

                if st.session_state.status_para_registrar:

                    with st.form("form_acao_final"):

                        st.markdown(f"**Ação selecionada:** {st.session_state.status_para_registrar}")

                        observacao = ""

                        if st.session_state.status_para_registrar == "Com Pendências":

                            observacao = st.text_area("Descreva as pendências:", key="obs_pendencia")

                        responsavel_acao = st.text_input("Seu nome (Responsável pela análise)")

                        if st.form_submit_button("Confirmar e Registrar Ação"):

                            if responsavel_acao:

                                df_historico = pd.DataFrame([{"Empresa": empresa_selecionada, "Status": st.session_state.status_para_registrar, "Observação": observacao, "Data da Ação": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Responsável": responsavel_acao}])

                                if salvar_dados_planilha(df_historico, "Historico_Liberacoes"):

                                    st.success(f"Ação '{st.session_state.status_para_registrar}' registrada com sucesso!")

                                    st.session_state.status_para_registrar = None

                            else: st.warning("Informe o seu nome como responsável.")

        except Exception as e:

            st.error(f"Ocorreu um erro ao carregar a página: {e}")



elif menu == "Cadastro Único Completo":

    st.header("Cadastro Único Completo")

    st.info("Cadastre empresa, funcionário e documentos iniciais (com upload) em um só lugar.")

    with st.form(key="form_unico_completo", clear_on_submit=False):

        with st.expander("1. Cadastrar Nova Empresa (Opcional)"):

            registrar_empresa = st.checkbox("Sim, desejo registrar uma nova empresa", value=True)

            nome_empresa = st.text_input("Nome da Empresa*", key="unico_emp_nome")

            cnpj = st.text_input("CNPJ*", key="unico_emp_cnpj")

            responsavel = st.text_input("Nome do Responsável", key="unico_emp_resp")

            telefone = st.text_input("Telefone", key="unico_emp_tel")

            email = st.text_input("E-mail", key="unico_emp_email")

        st.subheader("2. Dados do Funcionário")

        nome_func = st.text_input("Nome do Funcionário*", key="unico_func_nome")

        cpf = st.text_input("CPF*", key="unico_func_cpf")

        funcao = st.text_input("Função", key="unico_func_funcao")

        empresa_func = st.text_input("Empresa do Funcionário*", key="unico_func_empresa", value=nome_empresa if registrar_empresa and nome_empresa else "")

        data_admissao = st.date_input("Data de Admissão", key="unico_func_admissao")

        with st.expander("3. Registrar ASO Admissional (Opcional)"):

            registrar_aso = st.checkbox("Sim, desejo registrar o ASO", value=True, key="check_aso")

            aso_tipo = st.selectbox("Tipo de ASO", ["Admissional", "Periódico", "Demissional", "Mudança de Função", "Retorno ao Trabalho"], key="unico_aso_tipo")

            aso_data = st.date_input("Data do ASO", key="unico_aso_data")

            aso_validade = st.date_input("Validade do ASO", key="unico_aso_validade")

            aso_arquivo = st.file_uploader("Upload do ASO", type=['pdf', 'jpg', 'png', 'jpeg'], key="upload_aso")

        with st.expander("4. Registrar Treinamento Inicial (Opcional)"):

            registrar_treinamento = st.checkbox("Sim, desejo registrar um treinamento", value=True, key="check_train")

            treinamento_nome = st.text_input("Nome do Treinamento*", key="unico_train_nome")

            treinamento_data = st.date_input("Data do Treinamento", key="unico_train_data")

            treinamento_validade = st.date_input("Validade do Treinamento", key="unico_train_validade")

            treinamento_arquivo = st.file_uploader("Upload do Certificado de Treinamento", type=['pdf', 'jpg', 'png', 'jpeg'], key="upload_train")

        if st.form_submit_button("Salvar Cadastro Completo"):

            if not nome_func or not cpf or not empresa_func: st.warning("Preencha os campos obrigatórios do funcionário (*)")

            else:

                sucesso = True

                if registrar_empresa:

                    if nome_empresa and cnpj:

                        if not salvar_dados_planilha(pd.DataFrame([{"Nome da Empresa": nome_empresa, "CNPJ": cnpj, "Responsável": responsavel, "Telefone": telefone, "E-mail": email}]), "Empresas"): sucesso = False

                    else:

                        st.warning("Nome da Empresa e CNPJ são obrigatórios.")

                        sucesso = False

                if sucesso:

                    if not salvar_dados_planilha(pd.DataFrame([{"Nome": nome_func, "CPF": cpf, "Função": funcao, "Empresa": empresa_func, "Data de Admissão": data_admissao.strftime("%d/%m/%Y")}]), "Funcionários"): sucesso = False

                if sucesso and registrar_aso:

                    caminho_aso = salvar_arquivo(aso_arquivo, empresa_func, nome_func, "ASO")

                    if not salvar_dados_planilha(pd.DataFrame([{"Funcionário": nome_func, "Tipo de ASO": aso_tipo, "Data": aso_data.strftime("%d/%m/%Y"), "Validade": aso_validade.strftime("%d/%m/%Y"), "Arquivo": caminho_aso}]), "ASO"): sucesso = False

                if sucesso and registrar_treinamento:

                    if treinamento_nome:

                        caminho_trein = salvar_arquivo(treinamento_arquivo, empresa_func, nome_func, treinamento_nome)

                        df_treinamento = pd.DataFrame([{"Funcionário": nome_func, "Treinamento": treinamento_nome, "Data": treinamento_data.strftime("%d/%m/%Y"), "Validade": treinamento_validade.strftime("%d/%m/%Y"), "Arquivo": caminho_trein}])

                        if not salvar_dados_planilha(df_treinamento, "Treinamentos"): sucesso = False

                    else:

                        st.warning("O nome do treinamento é obrigatório.")

                        sucesso = False

                if sucesso:

                    st.success("Cadastro completo salvo com sucesso!")

                    st.balloons()



elif menu == "Cadastro da Empresa":

    st.header("Gerenciamento de Empresas")

    tab1, tab2 = st.tabs(["➕ Cadastrar Nova Empresa", "✏️ Gerenciar Empresas Existentes"])



    with tab1:

        st.subheader("Adicionar Nova Empresa")

        with st.form("form_nova_empresa", clear_on_submit=True):

            nome = st.text_input("Nome da Empresa*")

            cnpj = st.text_input("CNPJ*")

            responsavel = st.text_input("Nome do Responsável")

            telefone = st.text_input("Telefone")

            email = st.text_input("E-mail")

            if st.form_submit_button("Salvar Nova Empresa"):

                if nome and cnpj:

                    df_novo = pd.DataFrame([{"Nome da Empresa": nome, "CNPJ": cnpj, "Responsável": responsavel, "Telefone": telefone, "E-mail": email}])

                    if salvar_dados_planilha(df_novo, "Empresas"):

                        st.success(f"Empresa '{nome}' cadastrada com sucesso!")

                else:

                    st.warning("Nome e CNPJ são obrigatórios.")



    with tab2:

        st.subheader("Editar ou Excluir Empresa")

        try:

            sheets_dict = pd.read_excel(ARQUIVO_EXCEL, sheet_name=None)

            df_empresas = sheets_dict.get('Empresas', pd.DataFrame())

           

            if df_empresas.empty:

                st.info("Nenhuma empresa cadastrada para gerenciar.")

            else:

                lista_empresas = [""] + df_empresas['Nome da Empresa'].tolist()

                empresa_selecionada = st.selectbox("Selecione uma empresa", options=lista_empresas, key="select_gerenciar_empresa")



                if empresa_selecionada:

                    st.markdown("---")

                    dados_empresa = df_empresas[df_empresas['Nome da Empresa'] == empresa_selecionada].iloc[0]

                   

                    with st.form("form_editar_empresa"):

                        st.write(f"**Editando dados de: {empresa_selecionada}**")

                        novo_cnpj = st.text_input("CNPJ", value=dados_empresa['CNPJ'])

                        novo_responsavel = st.text_input("Responsável", value=dados_empresa.get('Responsável', ''))

                        novo_telefone = st.text_input("Telefone", value=dados_empresa.get('Telefone', ''))

                        novo_email = st.text_input("E-mail", value=dados_empresa.get('E-mail', ''))

                       

                        if st.form_submit_button("Atualizar Dados"):

                            idx = df_empresas.index[df_empresas['Nome da Empresa'] == empresa_selecionada][0]

                            df_empresas.loc[idx, 'CNPJ'] = novo_cnpj

                            df_empresas.loc[idx, 'Responsável'] = novo_responsavel

                            df_empresas.loc[idx, 'Telefone'] = novo_telefone

                            df_empresas.loc[idx, 'E-mail'] = novo_email

                           

                            sheets_dict['Empresas'] = df_empresas

                            if sobrescrever_abas(sheets_dict):

                                st.success("Dados da empresa atualizados com sucesso!")

                                st.rerun()



                    with st.expander("🗑️ Zona de Perigo - Excluir Empresa"):

                        st.warning(f"Atenção: Excluir a empresa '{empresa_selecionada}' removerá permanentemente todos os seus funcionários e registros associados (ASOs, Treinamentos).")

                       

                        if st.checkbox("Sim, eu entendo e desejo prosseguir.", key=f"delete_confirm_{empresa_selecionada}"):

                            if st.button("Excluir Empresa Permanentemente"):

                                df_funcionarios = sheets_dict.get('Funcionários', pd.DataFrame())

                                df_aso = sheets_dict.get('ASO', pd.DataFrame())

                                df_treinamentos = sheets_dict.get('Treinamentos', pd.DataFrame())

                               

                                funcionarios_a_excluir = df_funcionarios[df_funcionarios['Empresa'] == empresa_selecionada]['Nome'].tolist()

                               

                                sheets_dict['Empresas'] = df_empresas[df_empresas['Nome da Empresa'] != empresa_selecionada]

                                sheets_dict['Funcionários'] = df_funcionarios[df_funcionarios['Empresa'] != empresa_selecionada]

                                if not df_aso.empty and funcionarios_a_excluir:

                                    sheets_dict['ASO'] = df_aso[~df_aso['Funcionário'].isin(funcionarios_a_excluir)]

                                if not df_treinamentos.empty and funcionarios_a_excluir:

                                    sheets_dict['Treinamentos'] = df_treinamentos[~df_treinamentos['Funcionário'].isin(funcionarios_a_excluir)]



                                if sobrescrever_abas(sheets_dict):

                                    st.success(f"Empresa '{empresa_selecionada}' e todos os seus dados foram excluídos.")

                                    st.rerun()

        except Exception as e:

            st.error(f"Ocorreu um erro ao gerenciar empresas: {e}")



elif menu == "Cadastro de Funcionário":

    st.header("Gerenciamento de Funcionários")

    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Novo", "✏️ Gerenciar Existentes", "📋 Cadastrar em Lote"])



    with tab1:

        st.subheader("Adicionar Novo Funcionário")

        with st.form("form_novo_funcionario", clear_on_submit=True):

            nome = st.text_input("Nome do Funcionário*")

            cpf = st.text_input("CPF*")

            funcao = st.text_input("Função")

            try:

                lista_empresas = pd.read_excel(ARQUIVO_EXCEL, sheet_name='Empresas')['Nome da Empresa'].tolist()

                empresa = st.selectbox("Empresa*", options=[""] + lista_empresas)

            except Exception:

                empresa = st.text_input("Empresa*")

            data_admissao = st.date_input("Data de Admissão")

           

            if st.form_submit_button("Salvar Novo Funcionário"):

                if nome and cpf and empresa:

                    df_novo = pd.DataFrame([{"Nome": nome, "CPF": cpf, "Função": funcao, "Empresa": empresa, "Data de Admissão": data_admissao.strftime("%d/%m/%Y")}])

                    if salvar_dados_planilha(df_novo, "Funcionários"):

                        st.success(f"Funcionário '{nome}' cadastrado com sucesso!")

                else:

                    st.warning("Nome, CPF e Empresa são obrigatórios.")



    with tab2:

        st.subheader("Editar ou Excluir Funcionário")

        try:

            sheets_dict = pd.read_excel(ARQUIVO_EXCEL, sheet_name=None)

            df_empresas = sheets_dict.get('Empresas', pd.DataFrame())

            df_funcionarios = sheets_dict.get('Funcionários', pd.DataFrame())

           

            if df_funcionarios.empty:

                st.info("Nenhum funcionário cadastrado para gerenciar.")

            else:

                lista_empresas_gerenciar = [""] + df_empresas['Nome da Empresa'].tolist()

                empresa_selecionada = st.selectbox("Primeiro, selecione a empresa", options=lista_empresas_gerenciar, key="select_gerenciar_func_empresa")

               

                if empresa_selecionada:

                    funcionarios_da_empresa = df_funcionarios[df_funcionarios['Empresa'] == empresa_selecionada]

                    lista_funcionarios = [""] + funcionarios_da_empresa['Nome'].tolist()

                    funcionario_selecionado = st.selectbox("Agora, selecione o funcionário", options=lista_funcionarios, key="select_gerenciar_func")

                   

                    if funcionario_selecionado:

                        st.markdown("---")

                        dados_func = funcionarios_da_empresa[funcionarios_da_empresa['Nome'] == funcionario_selecionado].iloc[0]

                       

                        with st.form("form_editar_funcionario"):

                            st.write(f"**Editando dados de: {funcionario_selecionado}**")

                            novo_cpf = st.text_input("CPF", value=dados_func.get('CPF', ''))

                            nova_funcao = st.text_input("Função", value=dados_func.get('Função', ''))

                            try:

                                data_admissao_dt = datetime.strptime(dados_func.get('Data de Admissão', ''), '%d/%m/%Y').date()

                            except (ValueError, TypeError):

                                data_admissao_dt = datetime.now().date()

                            nova_data_admissao = st.date_input("Data de Admissão", value=data_admissao_dt)

                           

                            if st.form_submit_button("Atualizar Dados do Funcionário"):

                                idx = df_funcionarios.index[(df_funcionarios['Nome'] == funcionario_selecionado) & (df_funcionarios['Empresa'] == empresa_selecionada)][0]

                                df_funcionarios.loc[idx, 'CPF'] = novo_cpf

                                df_funcionarios.loc[idx, 'Função'] = nova_funcao

                                df_funcionarios.loc[idx, 'Data de Admissão'] = nova_data_admissao.strftime("%d/%m/%Y")

                                sheets_dict['Funcionários'] = df_funcionarios

                                if sobrescrever_abas(sheets_dict):

                                    st.success("Dados do funcionário atualizados com sucesso!")

                                    st.rerun()



                        with st.expander("🗑️ Zona de Perigo - Excluir Funcionário"):

                            st.warning(f"Atenção: Excluir o funcionário '{funcionario_selecionado}' removerá permanentemente seus registros de ASO e Treinamentos.")

                            if st.checkbox("Sim, eu entendo e desejo prosseguir.", key=f"delete_func_confirm"):

                                if st.button("Excluir Funcionário Permanentemente"):

                                    df_aso = sheets_dict.get('ASO', pd.DataFrame())

                                    df_treinamentos = sheets_dict.get('Treinamentos', pd.DataFrame())



                                    sheets_dict['Funcionários'] = df_funcionarios[df_funcionarios['Nome'] != funcionario_selecionado]

                                    if not df_aso.empty:

                                        sheets_dict['ASO'] = df_aso[df_aso['Funcionário'] != funcionario_selecionado]

                                    if not df_treinamentos.empty:

                                        sheets_dict['Treinamentos'] = df_treinamentos[df_treinamentos['Funcionário'] != funcionario_selecionado]



                                    if sobrescrever_abas(sheets_dict):

                                        st.success(f"Funcionário '{funcionario_selecionado}' e seus dados foram excluídos.")

                                        st.rerun()

        except Exception as e:

            st.error(f"Ocorreu um erro ao gerenciar funcionários: {e}")



    with tab3:

        st.subheader("Adicionar Múltiplos Funcionários em Lote")

        try:

            empresas_df = pd.read_excel(ARQUIVO_EXCEL, sheet_name='Empresas')

            lista_empresas = [""] + empresas_df['Nome da Empresa'].tolist()

            empresa_lote = st.selectbox("Selecione a Empresa para adicionar os funcionários", options=lista_empresas, key="lote_empresa")



            if empresa_lote:

                data_admissao_lote = st.date_input("Data de Admissão (para todos)", key="lote_data")

                placeholder_text = "Cole os dados aqui. Um funcionário por linha.\nFormato: Nome Completo,CPF,Função\n\nExemplo:\nJoão da Silva,111.111.111-11,Pintor\nMaria Oliveira,222.222.222-22,Soldadora"

                dados_lote = st.text_area("Dados dos Funcionários", height=250, placeholder=placeholder_text)

               

                if st.button("Salvar Funcionários em Lote"):

                    if dados_lote:

                        novos_funcionarios = []

                        linhas = dados_lote.strip().split('\n')

                        for i, linha in enumerate(linhas):

                            if not linha.strip(): continue

                            partes = [p.strip() for p in linha.split(',')]

                            if len(partes) >= 2:

                                nome, cpf = partes[0], partes[1]

                                funcao = partes[2] if len(partes) > 2 else ""

                                novos_funcionarios.append({"Nome": nome, "CPF": cpf, "Função": funcao, "Empresa": empresa_lote, "Data de Admissão": data_admissao_lote.strftime("%d/%m/%Y")})

                            else:

                                st.warning(f"A linha {i+1} ('{linha}') está em formato inválido e foi ignorada.")

                        if novos_funcionarios:

                            if salvar_dados_planilha(pd.DataFrame(novos_funcionarios), "Funcionários"):

                                st.success(f"{len(novos_funcionarios)} funcionários cadastrados com sucesso!")

                                st.balloons()

                        else: st.error("Nenhum dado válido foi encontrado para salvar.")

                    else: st.warning("O campo de dados dos funcionários está vazio.")

        except Exception as e:

            st.error(f"Ocorreu um erro no cadastro em lote: {e}")





elif menu == "Registrar ASO":

    st.header("Registro Individual de ASO")

    try:

        sheets_dict = pd.read_excel(ARQUIVO_EXCEL, sheet_name=None)

        df_empresas = sheets_dict.get('Empresas', pd.DataFrame())

        df_funcionarios = sheets_dict.get('Funcionários', pd.DataFrame())



        if df_empresas.empty or df_funcionarios.empty:

            st.warning("É necessário ter ao menos uma empresa e um funcionário cadastrados para registrar um ASO.")

        else:

            lista_empresas = [""] + df_empresas['Nome da Empresa'].tolist()

            empresa_selecionada = st.selectbox("1. Selecione a Empresa", options=lista_empresas, key="aso_empresa_select")



            if empresa_selecionada:

                funcionarios_da_empresa = df_funcionarios[df_funcionarios['Empresa'] == empresa_selecionada]

                lista_funcionarios = [""] + funcionarios_da_empresa['Nome'].tolist()

                funcionario_selecionado = st.selectbox("2. Selecione o Funcionário", options=lista_funcionarios, key="aso_func_select")



                if funcionario_selecionado:

                    with st.form("form_aso_ind", clear_on_submit=True):

                        st.write(f"Registrando ASO para **{funcionario_selecionado}** da empresa **{empresa_selecionada}**.")

                        tipo = st.selectbox("Tipo de ASO", ["Admissional", "Periódico", "Demissional", "Mudança de Função", "Retorno ao Trabalho"])

                        data = st.date_input("Data do ASO")

                        validade = st.date_input("Validade do ASO")

                        arquivo = st.file_uploader("Upload do arquivo do ASO", type=['pdf', 'jpg', 'png', 'jpeg'])

                       

                        if st.form_submit_button("Salvar ASO"):

                            caminho_arquivo_salvo = salvar_arquivo(arquivo, empresa_selecionada, funcionario_selecionado, "ASO")

                            df_novo = pd.DataFrame([{"Funcionário": funcionario_selecionado, "Tipo de ASO": tipo, "Data": data.strftime("%d/%m/%Y"), "Validade": validade.strftime("%d/%m/%Y"), "Arquivo": caminho_arquivo_salvo}])

                            if salvar_dados_planilha(df_novo, "ASO"):

                                st.success("ASO salvo com sucesso!")

                                st.balloons()

    except Exception as e:

        st.error(f"Ocorreu um erro ao carregar a página: {e}")



elif menu == "Registrar Treinamento":

    st.header("Registro Individual de Treinamento")

    try:

        sheets_dict = pd.read_excel(ARQUIVO_EXCEL, sheet_name=None)

        df_empresas = sheets_dict.get('Empresas', pd.DataFrame())

        df_funcionarios = sheets_dict.get('Funcionários', pd.DataFrame())



        if df_empresas.empty or df_funcionarios.empty:

            st.warning("É necessário ter ao menos uma empresa e um funcionário cadastrados para registrar um Treinamento.")

        else:

            lista_empresas = [""] + df_empresas['Nome da Empresa'].tolist()

            empresa_selecionada = st.selectbox("1. Selecione a Empresa", options=lista_empresas, key="trein_empresa_select")



            if empresa_selecionada:

                funcionarios_da_empresa = df_funcionarios[df_funcionarios['Empresa'] == empresa_selecionada]

                lista_funcionarios = [""] + funcionarios_da_empresa['Nome'].tolist()

                funcionario_selecionado = st.selectbox("2. Selecione o Funcionário", options=lista_funcionarios, key="trein_func_select")



                if funcionario_selecionado:

                    with st.form("form_train_ind", clear_on_submit=True):

                        st.write(f"Registrando Treinamento para **{funcionario_selecionado}** da empresa **{empresa_selecionada}**.")

                        treinamento = st.text_input("Nome do Treinamento*")

                        data = st.date_input("Data do Treinamento")

                        validade = st.date_input("Validade do Treinamento")

                        arquivo = st.file_uploader("Upload do certificado", type=['pdf', 'jpg', 'png', 'jpeg'])

                       

                        if st.form_submit_button("Salvar Treinamento"):

                            if treinamento:

                                caminho_arquivo_salvo = salvar_arquivo(arquivo, empresa_selecionada, funcionario_selecionado, treinamento)

                                df_novo = pd.DataFrame([{"Funcionário": funcionario_selecionado, "Treinamento": treinamento, "Data": data.strftime("%d/%m/%Y"), "Validade": validade.strftime("%d/%m/%Y"), "Arquivo": caminho_arquivo_salvo}])

                                if salvar_dados_planilha(df_novo, "Treinamentos"):

                                    st.success("Treinamento salvo com sucesso!")

                                    st.balloons()

                            else:

                                st.warning("O nome do treinamento é obrigatório.")

    except Exception as e:

        st.error(f"Ocorreu um erro ao carregar a página: {e}")
