import streamlit as st
import time
import random
import json

# --- CONFIGURAÇÃO DA PÁGINA (DEVE SER O PRIMEIRO COMANDO STREAMLIT) ---
st.set_page_config(layout="wide", page_title="Simulador Agente PF")

# --- CONSTANTES E CONFIGURAÇÕES DO SIMULADO (Agente PF) ---
# Baseado no Edital fornecido
TEMPO_TOTAL_SEGUNDOS = (4 * 3600) + (30 * 60)  # 4 horas e 30 minutos [cite: 407]
NUM_QUESTOES_BLOCO_1 = 60  # [cite: 404]
NUM_QUESTOES_BLOCO_2 = 36  # [cite: 404]
NUM_QUESTOES_BLOCO_3 = 24  # [cite: 404]
TOTAL_QUESTOES_PROVA = NUM_QUESTOES_BLOCO_1 + NUM_QUESTOES_BLOCO_2 + NUM_QUESTOES_BLOCO_3

# Critérios de Reprovação (será REPROVADO se nota INFERIOR a estes valores)
# Portanto, para APROVAÇÃO, a nota deve ser MAIOR OU IGUAL
MIN_PONTOS_BLOCO_1 = 6.00  # [cite: 442]
MIN_PONTOS_BLOCO_2 = 3.00  # [cite: 443]
MIN_PONTOS_BLOCO_3 = 2.00  # [cite: 444]
MIN_PONTOS_TOTAL = 48.00 # [cite: 444]
# --- FIM DAS CONFIGURAÇÕES ---

# --- FUNÇÕES AUXILIARES ---
def carregar_questoes_do_json(caminho_arquivo="questoes_pf_agente.json"):
    """Carrega as questões de um arquivo JSON."""
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            questoes = json.load(f)
        if not isinstance(questoes, list):
            print(f"LOG ERRO: Conteúdo do JSON não é uma lista.")
            return []
        if not all(isinstance(q, dict) for q in questoes):
            print(f"LOG ERRO: Nem todos os elementos da lista no JSON são dicionários (questões).")
            return []
        if not questoes:
            print(f"LOG AVISO: Arquivo JSON '{caminho_arquivo}' está vazio.")
            return []
        # Validação básica da estrutura de cada questão
        for i, q in enumerate(questoes):
            if not all(key in q for key in ['id', 'bloco', 'disciplina', 'enunciado', 'gabarito']):
                print(f"LOG AVISO: Questão {i} no JSON está com chaves faltando. ID: {q.get('id', 'N/A')}")
        return questoes
    except FileNotFoundError:
        print(f"LOG ERRO: Arquivo JSON '{caminho_arquivo}' não encontrado.")
        return []
    except json.JSONDecodeError as e:
        print(f"LOG ERRO: Erro ao decodificar o JSON do arquivo '{caminho_arquivo}': {e}")
        return []

def selecionar_questoes_simulado(questoes_disponiveis):
    """Seleciona aleatoriamente o número correto de questões para cada bloco."""
    if not questoes_disponiveis:
        return [{"id": f"ERRO_Q_{i}", "bloco": (i % 3) + 1, "disciplina": "Erro Carregamento", "enunciado": "Nenhuma questão pôde ser carregada. Verifique o arquivo JSON e o console.", "gabarito": "C"} for i in range(TOTAL_QUESTOES_PROVA)]

    random.shuffle(list(questoes_disponiveis)) # Embaralha uma cópia para variedade

    questoes_selecionadas_final = []
    blocos_config = {
        1: NUM_QUESTOES_BLOCO_1,
        2: NUM_QUESTOES_BLOCO_2,
        3: NUM_QUESTOES_BLOCO_3
    }

    for bloco_num, num_necessario in blocos_config.items():
        # Filtra questões disponíveis para o bloco atual
        questoes_do_bloco_disponiveis = [q for q in questoes_disponiveis if q.get('bloco') == bloco_num]
        
        selecao_para_este_bloco = []
        if len(questoes_do_bloco_disponiveis) >= num_necessario:
            # Se há questões suficientes únicas, seleciona sem repetição (ideal)
            selecao_para_este_bloco = random.sample(questoes_do_bloco_disponiveis, num_necessario)
        elif questoes_do_bloco_disponiveis: # Se há algumas, mas menos que o necessário
            print(f"LOG AVISO: Bloco {bloco_num} tem {len(questoes_do_bloco_disponiveis)} questões únicas, {num_necessario} são necessárias. Haverá repetição para este bloco.")
            selecao_para_este_bloco = random.choices(questoes_do_bloco_disponiveis, k=num_necessario)
        else: # Fallback se não há NENHUMA questão para o bloco no JSON
            print(f"LOG ERRO: Nenhuma questão disponível no JSON para o Bloco {bloco_num}. Usando placeholders.")
            selecao_para_este_bloco = [{"id": f"PLACEHOLDER_B{bloco_num}_{i}", "bloco": bloco_num, "disciplina": "Placeholder", "enunciado": f"Questão placeholder de emergência Bloco {bloco_num} - {i+1}", "gabarito": random.choice(["C", "E"])} for i in range(num_necessario)]
        
        questoes_selecionadas_final.extend(selecao_para_este_bloco)
    
    # Verificação final do total (embora a lógica acima deva garantir)
    if len(questoes_selecionadas_final) != TOTAL_QUESTOES_PROVA:
        print(f"LOG ERRO: Seleção final resultou em {len(questoes_selecionadas_final)} questões, esperado {TOTAL_QUESTOES_PROVA}. Preenchendo com placeholders.")
        # Preenche se faltar (situação de erro extremo)
        while len(questoes_selecionadas_final) < TOTAL_QUESTOES_PROVA:
            bloco_fallback = (len(questoes_selecionadas_final) % 3) + 1
            questoes_selecionadas_final.append({"id": f"TOTAL_FILL_PAD_{len(questoes_selecionadas_final)}", "bloco": bloco_fallback, "disciplina": "Placeholder Preenchimento", "enunciado": "Questão de preenchimento para totalizar.", "gabarito": "C"})
    
    return questoes_selecionadas_final


def calcular_pontuacao(respostas, questoes_simulado):
    """Calcula a pontuação baseada nas respostas e nos critérios do edital."""
    pontos_b1, corretas_b1, erradas_b1, brancas_b1 = 0.0, 0, 0, 0
    pontos_b2, corretas_b2, erradas_b2, brancas_b2 = 0.0, 0, 0, 0
    pontos_b3, corretas_b3, erradas_b3, brancas_b3 = 0.0, 0, 0, 0

    for questao in questoes_simulado:
        q_id = questao.get('id', f'unknown_id_{random.randint(1000,9999)}')
        bloco = questao.get('bloco')
        gabarito = questao.get('gabarito')
        resposta_usuario = respostas.get(q_id)

        # Pontuação Cebraspe: +1 para certa, -1 para errada, 0 para branca [cite: 433, 434, 435]
        if resposta_usuario is None or resposta_usuario == "Branco":
            if bloco == 1: brancas_b1 += 1
            elif bloco == 2: brancas_b2 += 1
            elif bloco == 3: brancas_b3 += 1
        elif resposta_usuario == gabarito:
            if bloco == 1: pontos_b1 += 1.0; corretas_b1 += 1
            elif bloco == 2: pontos_b2 += 1.0; corretas_b2 += 1
            elif bloco == 3: pontos_b3 += 1.0; corretas_b3 += 1
        else:  # Resposta errada
            if bloco == 1: pontos_b1 -= 1.0; erradas_b1 += 1
            elif bloco == 2: pontos_b2 -= 1.0; erradas_b2 += 1
            elif bloco == 3: pontos_b3 -= 1.0; erradas_b3 += 1
            
    pontos_total = pontos_b1 + pontos_b2 + pontos_b3
    
    # Critérios de aprovação (nota DEVE SER >= ao mínimo)
    aprovado_b1 = pontos_b1 >= MIN_PONTOS_BLOCO_1
    aprovado_b2 = pontos_b2 >= MIN_PONTOS_BLOCO_2
    aprovado_b3 = pontos_b3 >= MIN_PONTOS_BLOCO_3
    aprovado_total_pontos = pontos_total >= MIN_PONTOS_TOTAL
    
    status_aprovacao = "APROVADO(A) ✅"
    motivos_reprovacao = []

    aprovacao_final_nos_criterios = aprovado_b1 and aprovado_b2 and aprovado_b3 and aprovado_total_pontos

    if not aprovado_b1:
        motivos_reprovacao.append(f"Bloco I: {pontos_b1:.2f} (Mínimo necessário: {MIN_PONTOS_BLOCO_1:.2f})")
    if not aprovado_b2:
        motivos_reprovacao.append(f"Bloco II: {pontos_b2:.2f} (Mínimo necessário: {MIN_PONTOS_BLOCO_2:.2f})")
    if not aprovado_b3:
        motivos_reprovacao.append(f"Bloco III: {pontos_b3:.2f} (Mínimo necessário: {MIN_PONTOS_BLOCO_3:.2f})")
    if not aprovado_total_pontos: # Checa a pontuação total separadamente
         motivos_reprovacao.append(f"Pontuação Total: {pontos_total:.2f} (Mínimo necessário: {MIN_PONTOS_TOTAL:.2f})")

    if not aprovacao_final_nos_criterios:
        status_aprovacao = "REPROVADO(A) ❌"

    return {
        "B1": {"pontos": pontos_b1, "corretas": corretas_b1, "erradas": erradas_b1, "brancas": brancas_b1, "aprovado_no_bloco": aprovado_b1},
        "B2": {"pontos": pontos_b2, "corretas": corretas_b2, "erradas": erradas_b2, "brancas": brancas_b2, "aprovado_no_bloco": aprovado_b2},
        "B3": {"pontos": pontos_b3, "corretas": corretas_b3, "erradas": erradas_b3, "brancas": brancas_b3, "aprovado_no_bloco": aprovado_b3},
        "total_pontos": pontos_total,
        "aprovado_na_pontuacao_total": aprovado_total_pontos, # Se passou no critério da nota total
        "status_geral": status_aprovacao, # Se passou em TODOS os critérios
        "motivos_reprovacao": motivos_reprovacao
    }
# --- FIM DAS FUNÇÕES AUXILIARES ---


# --- CARREGAR QUESTÕES (EXECUTADO UMA VEZ NO INÍCIO) ---
if 'todas_questoes_base' not in st.session_state:
    json_questoes = carregar_questoes_do_json()
    if not json_questoes:
        st.session_state.todas_questoes_base = [
            {"id": "FALLBACK_B1_01", "bloco": 1, "disciplina": "Exemplo Fallback", "enunciado": "Questão exemplo fallback Bloco 1. Verifique 'questoes_pf_agente.json'.", "gabarito": "C"},
            {"id": "FALLBACK_B2_01", "bloco": 2, "disciplina": "Exemplo Fallback", "enunciado": "Questão exemplo fallback Bloco 2. Arquivo na mesma pasta?", "gabarito": "E"},
            {"id": "FALLBACK_B3_01", "bloco": 3, "disciplina": "Exemplo Fallback", "enunciado": "Questão exemplo fallback Bloco 3. JSON é uma lista de objetos?", "gabarito": "C"},
        ]
        st.session_state.json_load_error = True
    else:
        st.session_state.todas_questoes_base = json_questoes
        st.session_state.json_load_error = False
# --- FIM DO CARREGAMENTO DE QUESTÕES ---


# --- INTERFACE PRINCIPAL DO STREAMLIT ---
st.title("Simulador - Prova Objetiva Agente PF 👮‍♂️👮‍♀️")
st.markdown("---")

# Inicialização do estado da sessão se não existir
default_session_state = {
    'simulado_iniciado': False,
    'simulado_finalizado': False,
    'questoes_do_simulado': [],
    'respostas_usuario': {},
    'tempo_inicio': 0,
    'pagina_atual': 0
}
for key, value in default_session_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Feedback sobre carregamento de questões (na sidebar)
if 'json_load_error' in st.session_state:
    if st.session_state.json_load_error:
        st.sidebar.warning("⚠️ Falha ao carregar 'questoes_pf_agente.json'. Usando questões de exemplo internas. Verifique o console do terminal para logs.")
    else:
        st.sidebar.success(f"✅ {len(st.session_state.todas_questoes_base)} questões carregadas do JSON!")

# Lógica principal de exibição de telas
if st.session_state.simulado_iniciado and not st.session_state.simulado_finalizado:
    # --- TELA: SIMULADO EM ANDAMENTO ---
    tempo_decorrido = time.time() - st.session_state.tempo_inicio
    tempo_restante = TEMPO_TOTAL_SEGUNDOS - tempo_decorrido

    if tempo_restante <= 0:
        st.session_state.simulado_finalizado = True
        st.toast("Tempo esgotado!", icon="⏰")
        st.rerun()

    minutos_rest, segundos_rest = divmod(int(tempo_restante), 60)
    horas_rest, minutos_rest = divmod(minutos_rest, 60)
    
    st.sidebar.header("⏳ Tempo Restante")
    st.sidebar.subheader(f"{horas_rest:02d}:{minutos_rest:02d}:{segundos_rest:02d}")
    st.sidebar.info(f"**Questões:** {TOTAL_QUESTOES_PROVA} (B1: {NUM_QUESTOES_BLOCO_1}, B2: {NUM_QUESTOES_BLOCO_2}, B3: {NUM_QUESTOES_BLOCO_3})")
    st.sidebar.markdown("---")
    if st.sidebar.button("🏳️ Abandonar Simulado", type="secondary", key="btn_abandonar"):
        for key_to_reset in ['simulado_iniciado', 'simulado_finalizado', 'questoes_do_simulado', 'respostas_usuario', 'tempo_inicio', 'pagina_atual']:
            if key_to_reset in st.session_state:
                del st.session_state[key_to_reset]
        st.toast("Simulado abandonado.", icon="🏳️")
        st.rerun()
    st.sidebar.caption("Boa prova!")
    
    st.subheader("Questões da Prova Objetiva")
    st.caption(f"Instruções: Marque 'Certo', 'Errado' ou 'Branco'. Pontuação Cebraspe: +1 (Certa), -1 (Errada), 0 (Branca).")
    st.caption(f"Critérios de Aprovação (Agente PF): Bloco I ≥ {MIN_PONTOS_BLOCO_1:.0f}, Bloco II ≥ {MIN_PONTOS_BLOCO_2:.0f}, Bloco III ≥ {MIN_PONTOS_BLOCO_3:.0f}, Total ≥ {MIN_PONTOS_TOTAL:.0f} pontos.")
    st.markdown("---")

    # Controles de Paginação (FORA DO FORMULÁRIO)
    questoes_por_pagina = 10
    if not st.session_state.questoes_do_simulado:
        num_total_paginas = 1
    else:
        num_total_paginas = (len(st.session_state.questoes_do_simulado) + questoes_por_pagina - 1) // questoes_por_pagina
        if num_total_paginas == 0: num_total_paginas = 1

    if st.session_state.pagina_atual >= num_total_paginas: st.session_state.pagina_atual = num_total_paginas - 1
    if st.session_state.pagina_atual < 0: st.session_state.pagina_atual = 0

    nav_cols = st.columns([1, 3, 1])
    with nav_cols[0]:
        if st.session_state.pagina_atual > 0:
            if st.button("⬅️ Anterior", use_container_width=True, key="btn_anterior_paginacao"):
                st.session_state.pagina_atual -= 1
                st.rerun()
    with nav_cols[1]:
        st.markdown(f"<div style='text-align: center; margin-top: 8px;'>Página {st.session_state.pagina_atual + 1} de {num_total_paginas}</div>", unsafe_allow_html=True)
    with nav_cols[2]:
        if st.session_state.pagina_atual < num_total_paginas - 1:
            if st.button("Próxima ➡️", use_container_width=True, key="btn_proxima_paginacao"):
                st.session_state.pagina_atual += 1
                st.rerun()
    st.markdown("---")

    with st.form("simulado_form"):
        inicio_idx = st.session_state.pagina_atual * questoes_por_pagina
        fim_idx = inicio_idx + questoes_por_pagina
        
        questoes_pagina_atual = []
        if st.session_state.questoes_do_simulado:
            questoes_pagina_atual = st.session_state.questoes_do_simulado[inicio_idx:fim_idx]

        if not questoes_pagina_atual and st.session_state.questoes_do_simulado:
            st.warning("Não há questões para exibir nesta página.")
        
        for i, questao_obj in enumerate(questoes_pagina_atual, start=inicio_idx):
            st.markdown("---")
            q_id = questao_obj.get('id', f'radio_id_fallback_{i}')
            disciplina_q = questao_obj.get('disciplina', 'N/A')
            bloco_q = questao_obj.get('bloco', 'N/A')
            enunciado_q = questao_obj.get('enunciado', 'Enunciado não disponível.')

            st.markdown(f"**Questão {inicio_idx + i - inicio_idx + 1} (Bloco {bloco_q} - {disciplina_q})** ID: `{q_id}`")
            st.markdown(enunciado_q)
            
            default_index = 2 
            resposta_salva = st.session_state.respostas_usuario.get(q_id)
            if resposta_salva == "Certo": default_index = 0
            elif resposta_salva == "Errado": default_index = 1
            
            resposta = st.radio(
                "Sua resposta:", options=["Certo", "Errado", "Branco"],
                key=f"radio_key_{q_id}", 
                index=default_index,
                horizontal=True
            )
            if resposta == "Branco":
                 st.session_state.respostas_usuario[q_id] = None
            else:
                st.session_state.respostas_usuario[q_id] = resposta
        
        st.markdown("---")
        submitted = st.form_submit_button("🏁 Finalizar Simulado e Ver Resultado", type="primary", use_container_width=True)
        if submitted:
            st.session_state.simulado_finalizado = True
            st.rerun()

elif st.session_state.simulado_finalizado:
    # --- TELA: RESULTADOS DO SIMULADO ---
    st.balloons()
    st.header("🏁 Simulado Finalizado! 📊")
    
    if not st.session_state.questoes_do_simulado:
        st.error("Não há dados do simulado para exibir resultados. Tente iniciar um novo simulado.")
    else:
        resultado = calcular_pontuacao(st.session_state.respostas_usuario, st.session_state.questoes_do_simulado)
        
        st.subheader(f"Resultado Geral: {resultado['status_geral']}")

        if resultado['status_geral'] == "REPROVADO(A) ❌":
            st.warning("Critérios não atingidos:")
            for motivo in resultado['motivos_reprovacao']:
                st.caption(f"- {motivo}")
        
        st.markdown("---")
        st.subheader("Detalhes da Pontuação:")

        cols_resultado = st.columns(3)
        with cols_resultado[0]:
            st.metric(label="Pontos Bloco I", value=f"{resultado['B1']['pontos']:.2f} / {NUM_QUESTOES_BLOCO_1}")
            st.caption(f"C: {resultado['B1']['corretas']}, E: {resultado['B1']['erradas']}, B: {resultado['B1']['brancas']}")
            st.write(f"Status Bloco I: {'Aprovado ✔️' if resultado['B1']['aprovado_no_bloco'] else 'Reprovado ✖️'}")
        with cols_resultado[1]:
            st.metric(label="Pontos Bloco II", value=f"{resultado['B2']['pontos']:.2f} / {NUM_QUESTOES_BLOCO_2}")
            st.caption(f"C: {resultado['B2']['corretas']}, E: {resultado['B2']['erradas']}, B: {resultado['B2']['brancas']}")
            st.write(f"Status Bloco II: {'Aprovado ✔️' if resultado['B2']['aprovado_no_bloco'] else 'Reprovado ✖️'}")
        with cols_resultado[2]:
            st.metric(label="Pontos Bloco III", value=f"{resultado['B3']['pontos']:.2f} / {NUM_QUESTOES_BLOCO_3}")
            st.caption(f"C: {resultado['B3']['corretas']}, E: {resultado['B3']['erradas']}, B: {resultado['B3']['brancas']}")
            st.write(f"Status Bloco III: {'Aprovado ✔️' if resultado['B3']['aprovado_no_bloco'] else 'Reprovado ✖️'}")

        st.markdown("---")
        st.metric(label="PONTUAÇÃO TOTAL OBJETIVA", value=f"{resultado['total_pontos']:.2f} / {TOTAL_QUESTOES_PROVA}")
        st.write(f"Aprovado na pontuação total (critério isolado): {'Sim ✔️' if resultado['aprovado_na_pontuacao_total'] else 'Não ✖️'}")
        
        if st.button("🔁 Realizar Novo Simulado", key="novo_simulado_resultados_btn_final", use_container_width=True):
            # Limpar o estado da sessão para um novo simulado
            keys_to_clear = ['simulado_iniciado', 'simulado_finalizado', 'questoes_do_simulado', 
                             'respostas_usuario', 'tempo_inicio', 'pagina_atual']
            for key_to_reset in keys_to_clear:
                if key_to_reset in st.session_state:
                    del st.session_state[key_to_reset]
            # 'todas_questoes_base' e 'json_load_error' são carregados no início, não precisam ser limpos aqui.
            st.rerun()
        
        st.markdown("---")
        with st.expander("🔍 Ver Gabarito Detalhado e Suas Respostas"):
            if not st.session_state.questoes_do_simulado:
                 st.write("Nenhum gabarito para mostrar.")
            else:
                for q_idx, q_simulado in enumerate(st.session_state.questoes_do_simulado):
                    q_id_gabarito = q_simulado.get('id', f'gabarito_id_fallback_{q_idx}')
                    resp_usr_val = st.session_state.respostas_usuario.get(q_id_gabarito)
                    resp_usr_display = resp_usr_val if resp_usr_val is not None else "Branco"

                    cor_texto = "gray"
                    if resp_usr_val is not None:
                        cor_texto = "green" if resp_usr_val == q_simulado.get('gabarito') else "red"
                    
                    disciplina_gabarito = q_simulado.get('disciplina', 'N/A')
                    bloco_gabarito = q_simulado.get('bloco','N/A')
                    enunciado_gabarito = q_simulado.get('enunciado', 'Enunciado não disponível.')
                    gabarito_oficial = q_simulado.get('gabarito','N/A')

                    st.markdown(f"**Questão {q_idx + 1} (Bloco {bloco_gabarito} - {disciplina_gabarito} - ID: `{q_id_gabarito}` )**")
                    st.markdown(enunciado_gabarito)
                    st.markdown(f"Gabarito Oficial: **{gabarito_oficial}** | Sua Resposta: <span style='color:{cor_texto}; font-weight:bold;'>{resp_usr_display}</span>", unsafe_allow_html=True)
                    if q_idx < len(st.session_state.questoes_do_simulado) - 1:
                        st.markdown("---")
else:
    # --- TELA INICIAL ---
    st.subheader("Bem-vindo(a) ao Simulador para Agente da Polícia Federal! 🎯")
    st.markdown("""
    Este simulador foi projetado para te ajudar a treinar para a prova objetiva do concurso de Agente da Polícia Federal, seguindo o estilo da banca Cebraspe (CESPE).
    
    **Características:**
    - **120 questões** objetivas (Certo/Errado), divididas em 3 Blocos conforme o edital.
    - **Tempo total de prova:** 4 horas e 30 minutos (para refletir a duração da prova objetiva + discursiva).
    - **Sistema de correção Cebraspe:**
        - Resposta CORRETA: +1,00 ponto
        - Resposta ERRADA: -1,00 ponto
        - Sem marcação (Branco): 0,00 pontos
    - **Critérios de aprovação** aplicados ao final, baseados no edital.
    
    **Instruções:**
    1.  Certifique-se de que o arquivo `questoes_pf_agente.json` está na mesma pasta deste script.
    2.  Clique no botão abaixo para iniciar.
    3.  Gerencie seu tempo e responda a todas as questões.
    4.  Ao final, você verá sua pontuação detalhada e se foi aprovado(a) pelos critérios do edital.
    """)
    st.markdown("---")

    if not st.session_state.get('todas_questoes_base') or len(st.session_state.get('todas_questoes_base', [])) == 0:
        st.error("⚠️ **ERRO CRÍTICO:** Nenhuma questão pôde ser carregada (nem do JSON, nem do fallback interno).")
        st.error("Por favor, verifique:")
        st.markdown("- Se o arquivo `questoes_pf_agente.json` existe na mesma pasta deste script.")
        st.markdown("- Se o arquivo `questoes_pf_agente.json` está formatado corretamente (uma lista de objetos JSON, sem erros de sintaxe).")
        st.markdown("- O console do terminal (onde você rodou `streamlit run ...`) para mensagens de erro detalhadas durante o carregamento.")
        st.warning("O simulador não pode iniciar sem questões. Corrija o problema e atualize a página (F5 ou Ctrl+R).")
    else:
        if st.button("🚀 Iniciar Novo Simulado!", key="iniciar_simulado_btn_principal", use_container_width=True, type="primary"):
            st.session_state.questoes_do_simulado = selecionar_questoes_simulado(list(st.session_state.todas_questoes_base))
            
            # Validação robusta
            if not st.session_state.questoes_do_simulado or \
               len(st.session_state.questoes_do_simulado) != TOTAL_QUESTOES_PROVA or \
               not all(isinstance(q, dict) and 'id' in q for q in st.session_state.questoes_do_simulado):
                st.error("Falha crítica ao montar o conjunto de questões para o simulado. Verifique o banco de questões e a função 'selecionar_questoes_simulado'. Tente atualizar a página.")
                st.session_state.simulado_iniciado = False # Garante que não prossiga
            else:
                st.session_state.respostas_usuario = {q['id']: None for q in st.session_state.questoes_do_simulado}
                st.session_state.simulado_iniciado = True
                st.session_state.simulado_finalizado = False
                st.session_state.tempo_inicio = time.time()
                st.session_state.pagina_atual = 0 
                st.rerun()
