import telebot
import datetime
import pymongo
from unidecode import unidecode
import schedule
import requests
import os
import time

# //Configurações de acesso ao mongoDB//
cluster = pymongo.MongoClient('mongodb+srv://wender:wender@cluster0.mf8a2u5.mongodb.net/?retryWrites=true&w=majority')
db = cluster.get_database(('DragonTips'))
collection_cantolimiteHT = db.get_collection('cantoLimiteHT')
collection_cantolimiteFT = db.get_collection('cantoLimiteFT')
collection_over05FT = db.get_collection('Over05FT')
collection_over05HT = db.get_collection('Over05HT')
collection_config = db.get_collection('Configuracoes')
collection_resultadoDiario = db.get_collection('ResultadosDiarios')

resultado_config = collection_config.find_one({'name_group': 'DragonTips'})

# //Configuração e criação do bot do telegram//
token = resultado_config['token']
chat_id = resultado_config['chat_id']
figurinha = 'CAACAgEAAxkBAAEHlINj3Y2iaLHHr34Pyk1SSLDpnyRJeAACfwEAAjCsSUUfI-OmTvn8GS4E'
bot = telebot.TeleBot(token)

def data_atual():
    date_now = datetime.datetime.now()
    data_atual = f'{date_now.day}/{date_now.month}/{date_now.year}'
    return data_atual

def iniciar_bd_diario_resutados():
    dado = {
        'data':  data_atual,
        'green':0,
        'red': 0,
        }
    collection_resultadoDiario.insert_one(dado)
# //Trata o placar que vem no formato "0-0" separando o numero e retornando a soma do placar//
def tratarPlacar(placar):
    numbers = placar.split("-")
    number1 = int(numbers[0])
    number2 = int(numbers[1])
    result = number1 + number2
    return result

def relatorio_diario():
    date_now = datetime.datetime.now()
    data_atual = f'{date_now.day}/{date_now.month}/{date_now.year}'

    cluster = pymongo.MongoClient('mongodb+srv://wender:wender@cluster0.mf8a2u5.mongodb.net/?retryWrites=true&w=majority')
    db = cluster.get_database(('DragonTips'))
    collection_resultadoDiario = db.get_collection('ResultadosDiarios')
    resultado_bd = collection_resultadoDiario.find_one({'data': data_atual})

    resultado_dia = f'''
RESULTADO DO DIA <b>{data_atual}</b>

🔰 <b>{resultado_bd['green'] + resultado_bd['red']}</b> ALERTAS ENVIADOS
✅ <b>{resultado_bd['green']}</b> GREENS 
❌ <b>{resultado_bd['red']}</b> RED

<b>💎 COM UMA ASSERTIVIDADE DE {float((100 / (resultado_bd['green'] + resultado_bd['red'])) * resultado_bd['green']):.2f}%</b>'''

    msg = bot.send_message(chat_id=chat_id, text=resultado_dia, parse_mode="HTML", disable_web_page_preview="True")
    msg_id = msg.message_id
    bot.pin_chat_message(chat_id=chat_id, message_id=msg_id)


schedule.every().day.at("23:58").do(relatorio_diario)

while True:
    try:
        schedule.run_pending()

        date_now = datetime.datetime.now()
        data_atual = f'{date_now.day}/{date_now.month}/{date_now.year}'

        cluster = pymongo.MongoClient('mongodb+srv://wender:wender@cluster0.mf8a2u5.mongodb.net/?retryWrites=true&w=majority')
        db = cluster.get_database((('DragonTips')))
        collection_resultadoDiario = db.get_collection('ResultadosDiarios')
        resultado_bd = collection_resultadoDiario.find_one({'data': data_atual})

        if resultado_bd:
            pass
        else:
            iniciar_bd_diario_resutados()

        # //Listas que armazenam os ID de jogos ja enviados//
        cantolimiteHT_send = []
        cantolimiteFT_send = []
        over_05FT_send = []
        over_05HT_send = []

        # //API de onde extraimos as partidas//
        url = "https://api.sportsanalytics.com.br/api/v1/fixtures-svc/fixtures/livescores"
        querystring = {"include": "weatherReport,additionalInfo,league,stats,pressureStats,probabilities"}
        payload = ""
        headers = {
            "cookie": "route=f69973370a0dd0883a57c7b955dfc742; SRVGROUP=common",
            "authority": "api.sportsanalytics.com.br",
            "accept": "application/json, text/plain, */*",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://playscores.com",
            "referer": "https://playscores.com/",
            "sec-ch-ua": "^\^Google",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "^\^Windows^^",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        }
        response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
        if response.status_code == 200:
            dic_response = response.json()

            iniciando_analise = " Analisando  as partidas em LIVE (AO VIVO) "
            print(iniciando_analise.center(150, "="))
            print('')

            for jogo in dic_response['data']:
                # //data no formato AAAA/MM/DD//
                date = jogo['date']

                # //partidaID (Identificação unica da partida)//
                partidaId = jogo['fixtureId']

                # //status da partida (LIVE, HT, FT OU ET)//
                status_partida = jogo['status']

                # //Team (Dados de equipes e torneio)//
                awayTeam = jogo['awayTeam']['name']
                homeTeam = jogo['homeTeam']['name']
                league = jogo['league']['name']

                # //CurrentTime (Tempo atual da partida)//
                minute = 0 if jogo['currentTime']['minute'] is None else jogo['currentTime']['minute']
                second = jogo['currentTime']['second']

                # //Scores (Placar atual da partida)//
                homeTeamScore = jogo['scores']['homeTeamScore']
                awayTeamScore = jogo['scores']['awayTeamScore']
                htScore = jogo['scores']['htScore']
                ftScore = jogo['scores']['ftScore']

                # //Verificando se na partida tem estatisticas disponiveis//
                if 'stats' in jogo:
                    if jogo['stats'] != None:
                        # //corners (Escanteios)//
                        corners_home = jogo['stats']['corners']['home']
                        corners_away = jogo['stats']['corners']['away']

                        # //dangerousAttacks (Ataques perigosos)
                        ataquesPerigosos_Home = jogo['stats']['dangerousAttacks']['home']
                        ataquesPerigosos_Away = jogo['stats']['dangerousAttacks']['away']

                        # //shotsOffgoal (Chutes para fora)
                        chutesfora_Home = jogo['stats']['shotsOffgoal']['home']
                        chutesfora_Away = jogo['stats']['shotsOffgoal']['away']

                        # //shotsOngoal (Chutes no gol)//
                        chutesNogol_Home = jogo['stats']['shotsOngoal']['home']
                        chutesNogol_Away = jogo['stats']['shotsOngoal']['away']

                        # //yellowredcards (Cartões amarelo)//
                        yellowredcards_home = jogo['stats']['yellowredcards']['home']
                        yellowredcards_away = jogo['stats']['yellowredcards']['away']

                        # //possessiontime (Posse de bola)//
                        possessiontime_home = 0 if jogo['stats']["possessiontime"]['home'] is None else jogo['stats']["possessiontime"]['home']
                        possessiontime_away = 0 if jogo['stats']["possessiontime"]['away'] is None else jogo['stats']["possessiontime"]['away']

                # //Verificando se na partida tem indices de pressões disponiveis//
                if 'pressureStats' in jogo:
                    if jogo['pressureStats'] != None:
                        # //appm1 (Indica a média de ataques perigosos por minutos. Ataques perigosos dividido por tempo do jogo)//
                        appm1_home = 0 if jogo['pressureStats']['appm1']['home'] is None else jogo['pressureStats']['appm1']['home']
                        appm1_away = 0 if jogo['pressureStats']['appm1']['away'] is None else jogo['pressureStats']['appm1']['away']

                        # //appm2 (Mesma coisa do APM¹ porém checando somente os últimos 10 minutos)
                        appm2_home = 0 if jogo['pressureStats']['appm2']['home'] is None else jogo['pressureStats']['appm2']['home']
                        appm2_away = 0 if jogo['pressureStats']['appm2']['away'] is None else jogo['pressureStats']['appm2']['away']

                        # //exg (Indica a expectativa de gol. Considera apenas os últimos 10 minutos da partida. Chute no Gol + Chute fora + Cantos, entre outros inputs (métricas). Pontuação máxima de 2. Pontuação entre 1.50 a 2 mostra um cenário de muita pressão de uma determinada equipe)//
                        exg_home = 0 if jogo['pressureStats']['exg']['home'] is None else jogo['pressureStats']['exg']['home']
                        exg_away = 0 if jogo['pressureStats']['exg']['away'] is None else jogo['pressureStats']['exg']['away']

                        # //mh1 (Chance de gol e ele gera pontuação a partir dos dados de chute ao gol + posse de bola, + outros inputs. Valor ideal para uma única equipe a partir de 50, e a soma das duas equipes a partir de 60)//
                        mh1_home = 0 if jogo['pressureStats']['mh1']['home'] is None else jogo['pressureStats']['mh1']['home']
                        mh1_away = 0 if jogo['pressureStats']['mh1']['away'] is None else jogo['pressureStats']['mh1']['away']

                        # //mh2 (Posicionamento ofensivo da equipe, quando uma equipe está rodeando a área adversária sem muitas interrupções (por exemplo: faltas e escanteios). Valor ideal para uma única equipe a partir de 10, e a soma das duas equipes a partir de 15)//
                        mh2_home = 0 if jogo['pressureStats']['mh2']['home'] is None else jogo['pressureStats']['mh2']['home']
                        mh2_away = 0 if jogo['pressureStats']['mh2']['away'] is None else jogo['pressureStats']['mh2']['away']

                        # //mh3 (A soma da competição entre os índices. Qualquer valor de uma única equipe acima de 6 é um bom indicativo)//
                        mh3_home = 0 if jogo['pressureStats']['mh3']['home'] is None else jogo['pressureStats']['mh3']['home']
                        mh3_away = 0 if jogo['pressureStats']['mh3']['away'] is None else jogo['pressureStats']['mh3']['away']

                        # //attack_momentum (Poder de ataque da equipe)//
                        attack_momentum_home = 0 if jogo['pressureStats']['attack_momentum']['home'] is None else jogo['pressureStats']['attack_momentum']['home']
                        attack_momentum_away = 0 if jogo['pressureStats']['attack_momentum']['away'] is None else jogo['pressureStats']['attack_momentum']['away']

                if 'pressureStats' not in jogo:
                    appm1_home = 0
                    appm1_away = 0
                    appm2_home = 0
                    appm2_away = 0
                    exg_home = 0
                    exg_away = 0
                    mh1_home = 0
                    mh1_away = 0
                    mh2_home = 0
                    mh2_away = 0
                    mh3_home = 0
                    mh3_away = 0
                    attack_momentum_home = 0
                    attack_momentum_away = 0

                if 'probabilities' in jogo:
                    if jogo['probabilities'] != None:
                        AT_over_0_5 = 0 if jogo['probabilities']['AT_over_0_5'] is None else jogo['probabilities']['AT_over_0_5']
                        AT_over_1_5 = 0 if jogo['probabilities']['AT_over_1_5'] is None else jogo['probabilities']['AT_over_1_5']
                        AT_under_0_5 = 0 if jogo['probabilities']['AT_under_0_5'] is None else jogo['probabilities']['AT_under_0_5']
                        AT_under_1_5 = 0 if jogo['probabilities']['AT_under_1_5'] is None else jogo['probabilities']['AT_under_1_5']
                        HT_over_0_5 = 0 if jogo['probabilities']['HT_over_0_5'] is None else jogo['probabilities']['HT_over_0_5']
                        HT_over_1_5 = 0 if jogo['probabilities']['HT_over_1_5'] is None else jogo['probabilities']['HT_over_1_5']
                        HT_under_0_5 = 0 if jogo['probabilities']['HT_under_0_5'] is None else jogo['probabilities']['HT_under_0_5']
                        HT_under_1_5 = 0 if jogo['probabilities']['HT_under_1_5'] is None else jogo['probabilities']['HT_under_1_5']
                        home = 0 if jogo['probabilities']['home'] is None else jogo['probabilities']['home']
                        away = 0 if jogo['probabilities']['away'] is None else jogo['probabilities']['away']
                        btts = 0 if jogo['probabilities']['btts'] is None else jogo['probabilities']['btts']
                        draw = 0 if jogo['probabilities']['draw'] is None else jogo['probabilities']['draw']
                        over_0_5 = 0 if jogo['probabilities']['over_0_5'] is None else jogo['probabilities']['over_0_5']
                        over_1_5 = 0 if jogo['probabilities']['over_1_5'] is None else jogo['probabilities']['over_1_5']
                        over_2_5 = 0 if jogo['probabilities']['over_2_5'] is None else jogo['probabilities']['over_2_5']
                        over_3_5 = 0 if jogo['probabilities']['over_3_5'] is None else jogo['probabilities']['over_3_5']
                        under_0_5 = 0 if jogo['probabilities']['under_0_5'] is None else jogo['probabilities'][
                            'under_0_5']
                        under_1_5 = 0 if jogo['probabilities']['under_1_5'] is None else jogo['probabilities'][
                            'under_1_5']
                        under_2_5 = 0 if jogo['probabilities']['under_2_5'] is None else jogo['probabilities'][
                            'under_2_5']
                        under_3_5 = 0 if jogo['probabilities']['under_3_5'] is None else jogo['probabilities'][
                            'under_3_5']

                if 'probabilities' not in jogo:
                    AT_over_0_5 = 0
                    AT_over_1_5 = 0
                    AT_under_0_5 = 0
                    AT_under_1_5 = 0
                    HT_over_0_5 = 0
                    HT_over_1_5 = 0
                    HT_under_0_5 = 0
                    HT_under_1_5 = 0
                    home = 0
                    away = 0
                    btts = 0
                    draw = 0
                    over_0_5 = 0
                    over_1_5 = 0
                    over_2_5 = 0
                    over_3_5 = 0
                    under_0_5 = 0
                    under_1_5 = 0
                    under_2_5 = 0
                    under_3_5 = 0

                if jogo['stats'] != None and  jogo['pressureStats'] != None:
                    # //Soma para alerta (Limite e  +1)
                    canto_05 = (corners_home + corners_away) + 0.5
                    canto_01 = (corners_home + corners_away) + 1

                    # //CG (chutes gols + chutes para fora + escanteios)//
                    CG_home = chutesfora_Home+chutesNogol_Home+corners_home
                    CG_away = chutesfora_Away+chutesNogol_Away+corners_away

                    # //Rendimento (appm x posse de bola)//
                    rendimento_home = appm1_home * possessiontime_home
                    rendimento_away = appm1_away * possessiontime_away

                # //Verifica o time que tem menos caracteres, remove os acentos e cria link para partida na BET365//
                if len(homeTeam) < len(awayTeam):
                    timeMenosCaracteres = unidecode(homeTeam)
                else:
                    timeMenosCaracteres = unidecode(awayTeam)
                time_para_link = timeMenosCaracteres.replace(" ", "%20")  # //SUBSTITUI ESPAÇOS DO NOME DO TIME POR %20//
                time_para_link_formatado = time_para_link.replace("'", '')
                link_bet365 = f"https://bet365.com/#/AX/K%5E{time_para_link_formatado}/"  # //ACRESCENTA O NOME DO TIME AO LINK//

                partida_info = f"fixtureId: {partidaId} | {minute}' {status_partida} - {homeTeam} {homeTeamScore} X {awayTeamScore} {awayTeam} - Link: {link_bet365}"
                print(partida_info.center(150, " "))

                # //Estratégia para CANTO LIMITE HT//
                document = collection_cantolimiteHT.find_one({'fixtureId': partidaId})
                exists = bool(document)

                p1_cantoHT = (((homeTeamScore - awayTeamScore == 1) and (minute >= 37 and minute <= 42)) and ((appm2_home + appm2_away >= 1.25) and (appm1_home >= 1 or appm1_away >= 1))) and (CG_home >= 10 or CG_away >= 10)
                p2_cantoHT = (((homeTeamScore + awayTeamScore == 0) and (minute >= 36 and minute <= 40)) and (appm2_home + appm2_away >= 1.50)) and (chutesfora_Away+chutesNogol_Away >= 4 or chutesfora_Home+chutesNogol_Home >= 4) and (appm1_home >= 0.80 or appm1_away >= 0.80)
                p3_cantoHT = (((homeTeamScore - awayTeamScore == 0) and (minute >= 36 and minute <= 40)) and (appm2_home+appm2_away >= 1.25)) and (appm1_home >= 1.10 or appm1_away >=1.10) and (chutesfora_Away+chutesNogol_Away >= 5 or chutesfora_Home+chutesNogol_Home >= 5)

                if exists != True:
                    if jogo['pressureStats'] != None and jogo['stats'] != None:
                        if p1_cantoHT or p2_cantoHT or p3_cantoHT:
                            if p1_cantoHT:
                                estrategia = 'Canto Limite HT - 1'
                            else:
                                pass
                            if p2_cantoHT:
                                estrategia = 'Canto Limite HT - 2'
                            else:
                                pass
                            if p3_cantoHT:
                                estrategia = 'Canto Limite HT - 3'
                            else:
                                pass
                            msg_clHT = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {homeTeam} x {awayTeam}
🏆 <b>Competição:</b> {league}
🆚 <b>Placar:</b> {homeTeamScore} x {awayTeamScore}
⏰ <b>Tempo da Partida:</b> {minute}'

<b>Estatísticas até os {minute}' minutos</b>
⛳️ Escanteios: {corners_home} - {corners_away}
🔥 Ataques perigosos: {ataquesPerigosos_Home} - {ataquesPerigosos_Away}
🧨 APPM: {appm1_home:.2f} - {appm1_away:.2f}
🎯 Chutes no gol: {chutesNogol_Home} - {chutesNogol_Away}
💥 Chutes fora do gol: {chutesfora_Home} - {chutesfora_Away}

📲 <b>Link para o jogo:</b>
 <b> <a href='{link_bet365}'>Bet365</a> </b>

<b>Estratégia: ⛳️ {estrategia} ⛳️</b>
<b>Entrada Sugerida:</b> Cantos Asiáticos HT
⛳️ <b>+{canto_05}</b> 
⛳️ <b>+{canto_01}.0</b> <b>(Opcional)</b>
'''
                            fig = bot.send_sticker(chat_id=chat_id, sticker=figurinha)
                            fig_id = fig.message_id
                            time.sleep(3)
                            bot.delete_message(chat_id=chat_id, message_id=fig_id)
                            mensagem = bot.send_message(chat_id=chat_id, text=msg_clHT, parse_mode="HTML", disable_web_page_preview=True)
                            msg_id = mensagem.message_id
                            dado1 = {
                                'fixtureId': partidaId,
                                'msg_id': msg_id,
                                'homeTeam': homeTeam,
                                'awayTeam': awayTeam,
                                'league': league,
                                'minute': minute,
                                'homeTeamScore': homeTeamScore,
                                'awayTeamScore': awayTeamScore,
                                'corners_home': corners_home,
                                'corners_away': corners_away,
                                'dangerousAttacks_home': ataquesPerigosos_Home,
                                'dangerousAttacks_away': ataquesPerigosos_Away,
                                'appm1_home': appm1_home,
                                'appm1_away': appm1_away,
                                'shotsOngoal_home': chutesNogol_Home,
                                'shotsOngoal_away': chutesNogol_Away,
                                'shotsOffgoal_home': chutesfora_Home,
                                'shotsOffgoal_away': chutesfora_Away,
                                'estrategia': estrategia,
                                'canto_05': canto_05,
                                'canto_01': canto_01
                            }
                            collection_cantolimiteHT.insert_one(dado1)
                            time.sleep(2)

                # //Estratégia para cantos Limites FT//
                document = collection_over05FT.find_one({'fixtureId': partidaId})
                exists = bool(document)

                p1_cantoFT = (homeTeamScore + awayTeamScore == 0) and (minute >= 60 and minute <= 70) and (appm2_home + appm2_away >= 1.25) and (appm1_home >= 1.00 or appm1_away >= 1.00) and (chutesfora_Away+chutesNogol_Away >= 8 or chutesfora_Home+chutesNogol_Home >= 8)
                p2_cantoFT = (homeTeamScore + awayTeamScore == 0) and (minute >= 60 and minute <= 70) and (CG_home >= 12 or CG_away >= 12) and (appm1_home >= 1.20 or appm1_away >= 1.20)

                if exists != True:
                    if jogo['pressureStats'] != None and jogo['stats'] != None:
                        if p1_cantoFT or p2_cantoFT:
                            if p1_cantoFT:
                                estrategia = '+0.5 gols FT 1'
                            else:
                                pass
                            if p2_cantoFT:
                                estrategia = '+0.5 gols FT 2'
                            else:
                                pass
                            msg_clFT = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {homeTeam} x {awayTeam}
🏆 <b>Competição:</b> {league}
🆚 <b>Placar:</b> {homeTeamScore} x {awayTeamScore}
⏰ <b>Tempo da Partida:</b> {minute}'

<b>Estatísticas até os {minute}' minutos</b>
⛳️ Escanteios: {corners_home} - {corners_away}
🔥 Ataques perigosos: {ataquesPerigosos_Home} - {ataquesPerigosos_Away}
🧨 APPM: {appm1_home:.2f} - {appm1_away:.2f}
🎯 Chutes no gol: {chutesNogol_Home} - {chutesNogol_Away}
💥 Chutes fora do gol: {chutesfora_Home} - {chutesfora_Away}

📲 <b>Link para o jogo:</b>
 <b> <a href='{link_bet365}'>Bet365</a> </b>

<b>Estratégia: ⚽️ {estrategia} ⚽️ </b>
<b>Entrada Sugerida: +0.5 Gols FT</b>
⚽️ <b>+0.5 Gols</b> 
⚽️ <b>+1.0 Gols (Opcional)</b>
'''
                            fig = bot.send_sticker(chat_id=chat_id, sticker=figurinha)
                            fig_id = fig.message_id
                            time.sleep(3)
                            bot.delete_message(chat_id=chat_id, message_id=fig_id)
                            mensagem = bot.send_message(chat_id=chat_id, text=msg_clFT, parse_mode="HTML", disable_web_page_preview=True)
                            msg_id = mensagem.message_id
                            dado2 = {
                                'fixtureId': partidaId,
                                'msg_id': msg_id,
                                'homeTeam': homeTeam,
                                'awayTeam': awayTeam,
                                'league': league,
                                'minute': minute,
                                'homeTeamScore': homeTeamScore,
                                'awayTeamScore': awayTeamScore,
                                'corners_home': corners_home,
                                'corners_away': corners_away,
                                'dangerousAttacks_home': ataquesPerigosos_Home,
                                'dangerousAttacks_away': ataquesPerigosos_Away,
                                'appm1_home': appm1_home,
                                'appm1_away': appm1_away,
                                'shotsOngoal_home': chutesNogol_Home,
                                'shotsOngoal_away': chutesNogol_Away,
                                'shotsOffgoal_home': chutesfora_Home,
                                'shotsOffgoal_away': chutesfora_Away,
                                'estrategia': estrategia,
                                'canto_05': canto_05,
                                'canto_01': canto_01
                            }
                            collection_over05FT.insert_one(dado2)
                            time.sleep(2)

                # Estratégia para Over 0.5 gols HT
                document = collection_over05HT.find_one({'fixtureId': partidaId})
                exists = bool(document)

                p1_over05HT = (homeTeamScore+awayTeamScore == 0) and (appm1_away+appm1_home >= 1.50) and (minute >=15 and minute <= 25) and ( chutesNogol_Home >= 2 or chutesNogol_Away >= 2) and (appm1_home>=1 or appm1_away>=1)
                p2_over05HT = (((minute>=15) and (minute<=25)) and (appm1_home>=1.15) and (appm2_home >=1.15) and (CG_home >= 9) and (homeTeamScore+awayTeamScore==0)) or ((minute>=15) and (minute<=25) and (appm1_away>=1.15 or appm1_away >=1.15) and (CG_away >= 9))
                p3_over05HT = (homeTeamScore+awayTeamScore == 0) and (appm1_away+appm1_home >= 1.6) and (minute >=20 and minute <= 25) and (CG_away >= 9 or CG_home >= 9)

                if exists != True:
                    if jogo['pressureStats'] != None and jogo['stats'] != None:
                        if p1_over05HT or p2_over05HT or p3_over05HT:
                            if p1_over05HT:
                                estrategia = '+0.5 Gol HT 1'
                            else:
                                pass
                            if p2_over05HT:
                                estrategia = '+0.5 Gol HT 2'
                            else:
                                pass
                            if p3_over05HT:
                                estrategia = '+0.5 Gol HT 3'
                            else:
                                pass

                            msg_05ht = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {homeTeam} x {awayTeam}
🏆 <b>Competição:</b> {league}
🆚 <b>Placar:</b> {homeTeamScore} x {awayTeamScore}
⏰ <b>Tempo da Partida:</b> {minute}'

<b>Estatísticas até os {minute}' minutos</b>
⛳️ Escanteios: {corners_home} - {corners_away}
🔥 Ataques perigosos: {ataquesPerigosos_Home} - {ataquesPerigosos_Away}
🧨 APPM: {appm1_home:.2f} - {appm1_away:.2f}
🎯 Chutes no gol: {chutesNogol_Home} - {chutesNogol_Away}
💥 Chutes fora do gol: {chutesfora_Home} - {chutesfora_Away}

📲 <b>Link para o jogo:</b>
 <b> <a href='{link_bet365}'>Bet365</a> </b>

<b>Estratégia: ⚽️ {estrategia} ⚽️ </b>
<b>Entrada Sugerida: +0.5 Gols HT</b>
⚽️ <b>+0.5 Gols</b> 
⚽️ <b>+1.0 Gols (Opcional)</b>
'''
                            fig = bot.send_sticker(chat_id=chat_id, sticker=figurinha)
                            fig_id = fig.message_id
                            time.sleep(3)
                            bot.delete_message(chat_id=chat_id, message_id=fig_id)
                            mensagem = bot.send_message(chat_id=chat_id, text=msg_05ht, parse_mode="HTML", disable_web_page_preview=True)
                            msg_id = mensagem.message_id
                            dado3 = {
                                'fixtureId': partidaId,
                                'msg_id': msg_id,
                                'homeTeam': homeTeam,
                                'awayTeam': awayTeam,
                                'league': league,
                                'minute': minute,
                                'homeTeamScore': homeTeamScore,
                                'awayTeamScore': awayTeamScore,
                                'corners_home': corners_home,
                                'corners_away': corners_away,
                                'dangerousAttacks_home': ataquesPerigosos_Home,
                                'dangerousAttacks_away': ataquesPerigosos_Away,
                                'appm1_home': appm1_home,
                                'appm1_away': appm1_away,
                                'shotsOngoal_home': chutesNogol_Home,
                                'shotsOngoal_away': chutesNogol_Away,
                                'shotsOffgoal_home': chutesfora_Home,
                                'shotsOffgoal_away': chutesfora_Away,
                                'estrategia': estrategia,
                                'canto_05': canto_05,
                                'canto_01': canto_01
                            }
                            collection_over05HT.insert_one(dado3)
                            time.sleep(2)

                # Estratégia para cantos limite FT
                document = collection_cantolimiteFT.find_one({'fixtureId': partidaId})
                exists = bool(document)

                p1_cantoFt = (homeTeamScore + awayTeamScore == 0) and (minute >= 85 and minute <= 87) and (appm2_home + appm2_away >= 1.25) and (appm1_home >= 1.00 or appm1_away >= 1.00) and (chutesNogol_Home+chutesfora_Home >= 8 or chutesNogol_Away+chutesfora_Away >= 8)
                p2_cantoFt = (homeTeamScore - awayTeamScore == 1) and (minute >= 85 and minute <= 87) and (CG_home >= 12 or CG_away >= 12) and (appm1_home >= 1.20 or appm1_away >= 1.20)

                if exists != True:
                    if jogo['pressureStats'] != None and jogo['stats'] != None:
                        if p1_cantoFt or p2_cantoFt:
                            if p1_cantoFt:
                                estrategia = 'Canto Limite FT 1'
                            if p2_cantoFt:
                                estrategia = 'Canto Limite FT 2'
                            msg_clFT = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {homeTeam} x {awayTeam}
🏆 <b>Competição:</b> {league}
🆚 <b>Placar:</b> {homeTeamScore} x {awayTeamScore}
⏰ <b>Tempo da Partida:</b> {minute}'

<b>Estatísticas até os {minute}' minutos</b>
⛳️ Escanteios: {corners_home} - {corners_away}
🔥 Ataques perigosos: {ataquesPerigosos_Home} - {ataquesPerigosos_Away}
🧨 APPM: {appm1_home:.2f} - {appm1_away:.2f}
🎯 Chutes no gol: {chutesNogol_Home} - {chutesNogol_Away}
💥 Chutes fora do gol: {chutesfora_Home} - {chutesfora_Away}

📲 <b>Link para o jogo:</b>
 <b> <a href='{link_bet365}'>Bet365</a> </b>

<b>Estratégia: ⛳️ {estrategia} ⛳️</b>
<b>Entrada Sugerida:</b> Cantos Asiáticos FT
⛳️ <b>+{canto_05}</b> 
⛳️ <b>+{canto_01}.0</b> <b>(Opcional)</b>
'''
                            fig = bot.send_sticker(chat_id=chat_id, sticker=figurinha)
                            fig_id = fig.message_id
                            time.sleep(3)
                            bot.delete_message(chat_id=chat_id, message_id=fig_id)
                            mensagem = bot.send_message(chat_id=chat_id, text=msg_clFT, parse_mode="HTML",disable_web_page_preview=True)
                            msg_id = mensagem.message_id
                            dado4 = {
                                'fixtureId': partidaId,
                                'msg_id': msg_id,
                                'homeTeam': homeTeam,
                                'awayTeam': awayTeam,
                                'league': league,
                                'minute': minute,
                                'homeTeamScore': homeTeamScore,
                                'awayTeamScore': awayTeamScore,
                                'corners_home': corners_home,
                                'corners_away': corners_away,
                                'dangerousAttacks_home': ataquesPerigosos_Home,
                                'dangerousAttacks_away': ataquesPerigosos_Away,
                                'appm1_home': appm1_home,
                                'appm1_away': appm1_away,
                                'shotsOngoal_home': chutesNogol_Home,
                                'shotsOngoal_away': chutesNogol_Away,
                                'shotsOffgoal_home': chutesfora_Home,
                                'shotsOffgoal_away': chutesfora_Away,
                                'estrategia': estrategia,
                                'canto_05': canto_05,
                                'canto_01': canto_01
                            }
                            collection_cantolimiteFT.insert_one(dado4)
                            time.sleep(2)

        else:
            print("RETORNO DA API FALHOU AGUARDANDO 60 SEGUNDOS PARA TENTAR NOVAMENTE")
            time.sleep(60)

        print("")
        lista_correcao = " Listas de alertas enviados "
        print(lista_correcao.center(150, "="))
        print("")

        # Cria lista de partidas enviadas canto limite HT
        resultado = collection_cantolimiteHT.find({})
        for dado in resultado:
            item = dado['fixtureId']
            if item not in cantolimiteHT_send:
                cantolimiteHT_send.append(dado['fixtureId'])
        lista_cantoHT = f'Canto Limite HT - {cantolimiteHT_send}'
        print(lista_cantoHT.center(150, " "))

        # Cria lista de partidas enviadas canto limite FT
        resultado = collection_over05FT.find({})
        for dado in resultado:
            item = dado['fixtureId']
            if item not in over_05FT_send:
                over_05FT_send.append(dado['fixtureId'])
        lista_GOLFT = f'Over 0.5 FT- {over_05FT_send}'
        print(lista_GOLFT.center(150, " "))

        # Cria lista de partidas enviadas Over 0.5 HT
        resultado = collection_over05HT.find({})
        for dado in resultado:
            item = dado['fixtureId']
            if item not in over_05HT_send:
                over_05HT_send.append(dado['fixtureId'])
        lista_over_05HT_send = f'Over 0.5 HT- {over_05HT_send}'
        print(lista_over_05HT_send.center(150, " "))

        # Cria lista de partidas enviadas canto limite FT
        resultado = collection_cantolimiteFT.find({})
        for dado in resultado:
            item = dado['fixtureId']
            if item not in cantolimiteFT_send:
                cantolimiteFT_send.append(dado['fixtureId'])
        lista_cantolimiteFT = f'Canto Limite FT - {cantolimiteFT_send}'
        print(lista_cantolimiteFT.center(150, " "))

        print("")
        lista_correcao = " Correção de alertas enviados "
        print(lista_correcao.center(150, "="))
        print("")

        # // Correção Canto Limite HT//
        for item in cantolimiteHT_send:
            url = f"https://api.sportsanalytics.com.br/api/v1/fixtures-svc/fixtures/{item}"
            querystring = {"include":"weatherReport,additionalInfo,league,stats,pressureStats,probabilities"}
            payload = ""
            headers = {
                "cookie": "route=f69973370a0dd0883a57c7b955dfc742; SRVGROUP=common",
                "authority": "api.sportsanalytics.com.br",
                "accept": "application/json, text/plain, */*",
                "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "origin": "https://playscores.com",
                "referer": "https://playscores.com/",
                "sec-ch-ua": "^\^Google",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "^\^Windows^^",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
            }
            response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
            if response.status_code == 200:
                dic_response = response.json()

                htScore = dic_response['data'][0]['scores']['htScore']
                status_partida = dic_response['data'][0]['status']
                minute_atual = dic_response['data'][0]['currentTime']['minute']
                corners_homeHT = dic_response['data'][0]['stats']['corners']['home']
                corners_awayHT = dic_response['data'][0]['stats']['corners']['away']

                resultado_bd = collection_cantolimiteHT.find_one({'fixtureId': item})

                bd_fixtureId = resultado_bd['fixtureId']
                bd_msg_id = resultado_bd['msg_id']
                bd_homeTeam = resultado_bd['homeTeam']
                bd_awayTeam = resultado_bd['awayTeam']
                bd_league = resultado_bd['league']
                bd_minute = resultado_bd['minute']
                bd_homeTeamScore = resultado_bd['homeTeamScore']
                bd_awayTeamScore = resultado_bd['awayTeamScore']
                bd_corners_home = resultado_bd['corners_home']
                bd_corners_away = resultado_bd['corners_away']
                bd_dangerousAttacks_home = resultado_bd['dangerousAttacks_home']
                bd_dangerousAttacks_away = resultado_bd['dangerousAttacks_away']
                bd_appm1_home = resultado_bd['appm1_home']
                bd_appm1_away = resultado_bd['appm1_away']
                bd_shotsOngoal_home = resultado_bd['shotsOngoal_home']
                bd_shotsOngoal_away = resultado_bd['shotsOngoal_away']
                bd_shotsOffgoal_home = resultado_bd['shotsOffgoal_home']
                bd_shotsOffgoal_away = resultado_bd['shotsOffgoal_away']
                bd_estrategia = resultado_bd['estrategia']
                bd_canto_05 = resultado_bd['canto_05']
                bd_canto_01 = resultado_bd['canto_01']

                filter = {'fixtureId': bd_fixtureId}

                if htScore is None or status_partida != "HT":
                    partida_andamento_05ht = f'CANTO LIMITE HT - {item} - {bd_homeTeam} X {bd_awayTeam} - Partida em andamento'
                    print(partida_andamento_05ht.center(150, " "))

                if minute_atual == 45 and status_partida == "HT":
                    if (corners_homeHT + corners_awayHT) == bd_canto_01:
                        correcao_clHT = f'''<b>🚨 Futebol Stats 🚨</b>             
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_away}

<b>Estratégia: ⛳️ {bd_estrategia} ⛳️</b>
<b>Entrada Sugerida:</b> Cantos Asiáticos HT
⛳️ <b>+{bd_canto_05} - Green ✅✅✅</b>
⛳️ <b>+{bd_canto_01}.0 - Reembolso 🔁🔁🔁</b>
'''
                        bot.edit_message_text(text=correcao_clHT, chat_id=chat_id, message_id=bd_msg_id, parse_mode="HTML")
                        collection_cantolimiteHT.delete_many(filter)
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'green': resultados_bd['green'] + 1}})
                        time.sleep(2)
                        partida_corrigida_clht = f'CANTO LIMITE HT - {item} | {bd_homeTeam} - {bd_awayTeam} | Green ✅✅✅ - Reembolso 🔁🔁🔁'
                        print(partida_corrigida_clht.center(150," "))

                    if (corners_homeHT + corners_awayHT) > bd_canto_01:
                        correcao_clHT2 = f'''<b>🚨 Futebol Stats 🚨</b>             
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_away}

<b>Estratégia: ⛳️ {bd_estrategia} ⛳️</b>
<b>Entrada Sugerida:</b> Cantos Asiáticos HT
⛳️ <b>+{bd_canto_05} - Green ✅✅✅</b>
⛳️ <b>+{bd_canto_01}.0 - Green ✅✅✅</b>
'''
                        bot.edit_message_text(text=correcao_clHT2, chat_id=chat_id, message_id=bd_msg_id,parse_mode="HTML")
                        collection_cantolimiteHT.delete_many(filter)
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'green': resultados_bd['green'] + 1}})
                        time.sleep(2)
                        partida_corrigida_clht = f'CANTO LIMITE HT - {item} | {bd_homeTeam} - {bd_awayTeam} | Green ✅✅✅ - Green ✅✅✅'
                        print(partida_corrigida_clht.center(150," "))

                    if (corners_homeHT + corners_awayHT) < bd_canto_05:
                        correcao_clHT3 = f'''<b>🚨 Futebol Stats 🚨</b>             
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_away}

<b>Estratégia: ⛳️ {bd_estrategia} ⛳️</b>
<b>Entrada Sugerida:</b> Cantos Asiáticos HT 
⛳️ <b>+{bd_canto_05} - Red ❌❌❌️</b>
⛳️ <b>+{bd_canto_01}.0 - Red ❌❌❌️</b>
'''
                        bot.edit_message_text(text=correcao_clHT3, chat_id=chat_id, message_id=bd_msg_id,parse_mode="HTML")
                        collection_cantolimiteHT.delete_many(filter)
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one( {'data': data_atual},{'$set':{'red': resultados_bd['red']+1}})
                        time.sleep(2)
                        partida_corrigida_clht = f'CANTO LIMITE HT - {item} | {bd_homeTeam} - {bd_awayTeam} | Red ❌❌❌️ - Red ❌❌❌️'
                        print(partida_corrigida_clht.center(150, " "))

            else:
                print("RETORNO DA API FALHOU AGUARDANDO 60 SEGUNDOS PARA TENTAR NOVAMENTE")
                time.sleep(60)

        for item in over_05FT_send:
            url = f"https://api.sportsanalytics.com.br/api/v1/fixtures-svc/fixtures/{item}"
            querystring = {"include":"weatherReport,additionalInfo,league,stats,pressureStats,probabilities"}
            payload = ""
            headers = {
                "cookie": "route=f69973370a0dd0883a57c7b955dfc742; SRVGROUP=common",
                "authority": "api.sportsanalytics.com.br",
                "accept": "application/json, text/plain, */*",
                "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "origin": "https://playscores.com",
                "referer": "https://playscores.com/",
                "sec-ch-ua": "^\^Google",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "^\^Windows^^",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
            }

            response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
            if response.status_code == 200:
                dic_response = response.json()

                ftScore = dic_response['data'][0]['scores']['ftScore']
                status_partida = dic_response['data'][0]['status']
                minute_atual = dic_response['data'][0]['currentTime']['minute']
                corners_home1 = dic_response['data'][0]['stats']['corners']['home']
                corners_away1 = dic_response['data'][0]['stats']['corners']['away']

                resultado_bd = collection_over05FT.find_one({'fixtureId': item})

                bd_fixtureId = resultado_bd['fixtureId']
                bd_msg_id = resultado_bd['msg_id']
                bd_homeTeam = resultado_bd['homeTeam']
                bd_awayTeam = resultado_bd['awayTeam']
                bd_league = resultado_bd['league']
                bd_minute = resultado_bd['minute']
                bd_homeTeamScore = resultado_bd['homeTeamScore']
                bd_awayTeamScore = resultado_bd['awayTeamScore']
                bd_corners_home = resultado_bd['corners_home']
                bd_corners_away = resultado_bd['corners_away']
                bd_dangerousAttacks_home = resultado_bd['dangerousAttacks_home']
                bd_dangerousAttacks_away = resultado_bd['dangerousAttacks_away']
                bd_appm1_home = resultado_bd['appm1_home']
                bd_appm1_away = resultado_bd['appm1_away']
                bd_shotsOngoal_home = resultado_bd['shotsOngoal_home']
                bd_shotsOngoal_away = resultado_bd['shotsOngoal_away']
                bd_shotsOffgoal_home = resultado_bd['shotsOffgoal_home']
                bd_shotsOffgoal_away = resultado_bd['shotsOffgoal_away']
                bd_estrategia = resultado_bd['estrategia']
                bd_canto_05 = resultado_bd['canto_05']
                bd_canto_01 = resultado_bd['canto_01']

                filter = {'fixtureId': bd_fixtureId}


                if ftScore is None or status_partida != "FT":
                    partida_andamento_05ft = f'Over 0.5 FT - {bd_homeTeam} - {bd_awayTeam} - Partida em andamento'
                    print(partida_andamento_05ft.center(150, " "))

                if status_partida == "FT":
                    if tratarPlacar(ftScore) == 1:
                        msg_2 = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_home}

<b>Estratégia: ⚽️ {bd_estrategia} ⚽️ </b>
<b>Entrada Sugerida:</b> +0.5 Gols FT
⚽️ <b>+0.5 Gols - Green ✅✅✅</b>
⚽️ <b>+1.0 Gols - Reembolso 🔁🔁🔁</b>
'''
                        bot.edit_message_text(text=msg_2, chat_id=chat_id, message_id=bd_msg_id, parse_mode="HTML")
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'green': resultados_bd['green'] + 1}})
                        time.sleep(2)
                        partida_corrigida_clht = f'Over 0.5 FT - {item} | {bd_homeTeam} - {bd_awayTeam} | Green ✅✅✅ - Reembolso 🔁🔁🔁'
                        print(partida_corrigida_clht.center(150, " "))
                        collection_over05FT.delete_many(filter)

                    if tratarPlacar(ftScore) > 1:
                        msg_21 = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_home}

<b>Estratégia: ⚽️ {bd_estrategia} ⚽️ </b>
<b>Entrada Sugerida:</b> +0.5 Gols FT
⚽️ <b>+0.5 Gols - Green ✅✅✅</b>
⚽️ <b>+1.0 Gols - Green ✅✅✅</b>
'''
                        bot.edit_message_text(text=msg_21, chat_id=chat_id, message_id=bd_msg_id, parse_mode="HTML")
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'green': resultados_bd['green'] + 1}})
                        time.sleep(2)
                        partida_corrigida_05ft = f'Over 0.5 FT - {item} | {bd_homeTeam} - {bd_awayTeam} | Green ✅✅✅ - Green ✅✅✅'
                        print(partida_corrigida_05ft.center(150, " "))
                        collection_over05FT.delete_many(filter)


                    if tratarPlacar(ftScore) == 0:
                         msg_211 = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_home}

<b>Estratégia: ⚽️ {bd_estrategia} ⚽️ </b>
<b>Entrada Sugerida:</b> +0.5 Gols FT
⚽️ <b>+0.5 Gols - Red ❌❌❌️</b>
⚽️ <b>+1.0 Gols  - Red ❌❌❌️</b>
'''
                    bot.edit_message_text(text=msg_211, chat_id=chat_id, message_id=bd_msg_id, parse_mode="HTML")
                    resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                    collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'red': resultados_bd['red'] + 1}})
                    time.sleep(2)
                    partida_corrigida_05ft = f'Over 0.5 FT - {item} | {bd_homeTeam} - {bd_awayTeam} | Red ❌❌❌️ - Red ❌❌❌️'
                    print(partida_corrigida_05ft.center(150, " "))
                    collection_over05FT.delete_many(filter)

            else:
                print("RETORNO DA API FALHOU AGUARDANDO 60 SEGUNDOS PARA TENTAR NOVAMENTE")
                time.sleep(60)

        for item in over_05HT_send:
            url = f"https://api.sportsanalytics.com.br/api/v1/fixtures-svc/fixtures/{item}"
            querystring = {"include":"weatherReport,additionalInfo,league,stats,pressureStats,probabilities"}
            payload = ""
            headers = {
                "cookie": "route=f69973370a0dd0883a57c7b955dfc742; SRVGROUP=common",
                "authority": "api.sportsanalytics.com.br",
                "accept": "application/json, text/plain, */*",
                "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "origin": "https://playscores.com",
                "referer": "https://playscores.com/",
                "sec-ch-ua": "^\^Google",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "^\^Windows^^",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
            }

            response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
            if response.status_code == 200:
                dic_response = response.json()

                htScore = dic_response['data'][0]['scores']['htScore']
                status_partida = dic_response['data'][0]['status']
                minute_atual = dic_response['data'][0]['currentTime']['minute']
                corners_home1 = dic_response['data'][0]['stats']['corners']['home']
                corners_away1 = dic_response['data'][0]['stats']['corners']['away']

                resultado_bd = collection_over05HT.find_one({'fixtureId': item})

                bd_fixtureId = resultado_bd['fixtureId']
                bd_msg_id = resultado_bd['msg_id']
                bd_homeTeam = resultado_bd['homeTeam']
                bd_awayTeam = resultado_bd['awayTeam']
                bd_league = resultado_bd['league']
                bd_minute = resultado_bd['minute']
                bd_homeTeamScore = resultado_bd['homeTeamScore']
                bd_awayTeamScore = resultado_bd['awayTeamScore']
                bd_corners_home = resultado_bd['corners_home']
                bd_corners_away = resultado_bd['corners_away']
                bd_dangerousAttacks_home = resultado_bd['dangerousAttacks_home']
                bd_dangerousAttacks_away = resultado_bd['dangerousAttacks_away']
                bd_appm1_home = resultado_bd['appm1_home']
                bd_appm1_away = resultado_bd['appm1_away']
                bd_shotsOngoal_home = resultado_bd['shotsOngoal_home']
                bd_shotsOngoal_away = resultado_bd['shotsOngoal_away']
                bd_shotsOffgoal_home = resultado_bd['shotsOffgoal_home']
                bd_shotsOffgoal_away = resultado_bd['shotsOffgoal_away']
                bd_estrategia = resultado_bd['estrategia']
                bd_canto_05 = resultado_bd['canto_05']
                bd_canto_01 = resultado_bd['canto_01']

                filter = {'fixtureId': bd_fixtureId}

                if htScore is None or status_partida != "HT":
                    partida_andamento_05ft = f'Over 0.5 HT - {bd_homeTeam} - {bd_awayTeam} - Partida em andamento'
                    print(partida_andamento_05ft.center(150, " "))


                if minute_atual == 45 and status_partida == 'HT':
                    if tratarPlacar(htScore) == 1:
                        mdg_ht = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_home}

<b>Estratégia: ⚽️ {bd_estrategia}⚽️ </b>
<b>Entrada Sugerida:</b> +0.5 Gols HT
⚽️ <b>+0.5 Gols - Green ✅✅✅</b>
⚽️ <b>+1.0 Gols - Reembolso 🔁🔁🔁</b>
        '''
                        bot.edit_message_text(text=mdg_ht, chat_id=chat_id, message_id=bd_msg_id, parse_mode="HTML")
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'green': resultados_bd['green'] + 1}})
                        time.sleep(2)
                        partida_corrigida_clht = f'Over 0.5 FT - {item} | {bd_homeTeam} - {bd_awayTeam} | Green ✅✅✅ - Reembolso 🔁🔁🔁'
                        print(partida_corrigida_clht.center(150, " "))
                        collection_over05HT.delete_many(filter)

                    if tratarPlacar(htScore) >= 2:
                        mdg_ht = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_home}

<b>Estratégia: ⚽️ {bd_estrategia} ⚽️ </b>
<b>Entrada Sugerida:</b> +0.5 Gols HT
⚽️ <b>+0.5 Gols - Green ✅✅✅</b>
⚽️ <b>+1.0 Gols - Green ✅✅✅</b>
                                '''
                        bot.edit_message_text(text=mdg_ht, chat_id=chat_id, message_id=bd_msg_id, parse_mode="HTML")
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'green': resultados_bd['green'] + 1}})
                        time.sleep(2)
                        partida_corrigida_clht = f'Over 0.5 FT - {item} | {bd_homeTeam} - {bd_awayTeam} | Green ✅✅✅ - Green ✅✅✅'
                        print(partida_corrigida_clht.center(150, " "))
                        collection_over05HT.delete_many(filter)

                    if tratarPlacar(htScore) == 0:
                        mdg_ht = f'''<b>🚨 Futebol Stats 🚨</b>            
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_home}

<b>Estratégia: ⚽️ {bd_estrategia} ⚽️ </b>
<b>Entrada Sugerida:</b> +0.5 Gols HT
⚽️ <b>+0.5 Gols - Red ❌❌❌️</b>
⚽️ <b>+1.0 Gols - Red ❌❌❌️</b>
                                '''
                        bot.edit_message_text(text=mdg_ht, chat_id=chat_id, message_id=bd_msg_id,parse_mode="HTML")
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'red': resultados_bd['red'] + 1}})
                        time.sleep(2)
                        partida_corrigida_clht = f'Over 0.5 FT - {item} | {bd_homeTeam} - {bd_awayTeam} | Red ❌❌❌️ - Red ❌❌❌️'
                        print(partida_corrigida_clht.center(150, " "))
                        collection_over05HT.delete_many(filter)
            else:
                print("RETORNO DA API FALHOU AGUARDANDO 60 SEGUNDOS PARA TENTAR NOVAMENTE")
                time.sleep(60)

        for item in cantolimiteFT_send:

            url = f"https://api.sportsanalytics.com.br/api/v1/fixtures-svc/fixtures/{item}"
            querystring = {"include": "stats"}
            payload = ""
            headers = {"cookie": "route=f69973370a0dd0883a57c7b955dfc742; SRVGROUP=common"}
            response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
            if response.status_code == 200:
                dic_response = response.json()

                ftScore = dic_response['data'][0]['scores']['ftScore']
                status_partida = dic_response['data'][0]['status']
                minute_atual = dic_response['data'][0]['currentTime']['minute']
                corners_home1 = dic_response['data'][0]['stats']['corners']['home']
                corners_away1 = dic_response['data'][0]['stats']['corners']['away']

                resultado_bd = collection_cantolimiteFT.find_one({'fixtureId': item})

                bd_fixtureId = resultado_bd['fixtureId']
                bd_msg_id = resultado_bd['msg_id']
                bd_homeTeam = resultado_bd['homeTeam']
                bd_awayTeam = resultado_bd['awayTeam']
                bd_league = resultado_bd['league']
                bd_minute = resultado_bd['minute']
                bd_homeTeamScore = resultado_bd['homeTeamScore']
                bd_awayTeamScore = resultado_bd['awayTeamScore']
                bd_corners_home = resultado_bd['corners_home']
                bd_corners_away = resultado_bd['corners_away']
                bd_dangerousAttacks_home = resultado_bd['dangerousAttacks_home']
                bd_dangerousAttacks_away = resultado_bd['dangerousAttacks_away']
                bd_appm1_home = resultado_bd['appm1_home']
                bd_appm1_away = resultado_bd['appm1_away']
                bd_shotsOngoal_home = resultado_bd['shotsOngoal_home']
                bd_shotsOngoal_away = resultado_bd['shotsOngoal_away']
                bd_shotsOffgoal_home = resultado_bd['shotsOffgoal_home']
                bd_shotsOffgoal_away = resultado_bd['shotsOffgoal_away']
                bd_estrategia = resultado_bd['estrategia']
                bd_canto_05 = resultado_bd['canto_05']
                bd_canto_01 = resultado_bd['canto_01']

                filter = {'fixtureId': bd_fixtureId}

                if ftScore is None or status_partida != "FT":
                    partida_andamento_05ft = f'CANTO LIMITE FT - {bd_homeTeam} - {bd_awayTeam} - Partida em andamento'
                    print(partida_andamento_05ft.center(150, " "))
                if status_partida == "FT":
                    if (corners_home1 + corners_away1) == bd_canto_01:
                        correcao_clFT = f'''<b>🚨 Futebol Stats 🚨</b> 
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_home}

<b>Estratégia: ⛳️ {bd_estrategia} ⛳️</b>
<b>Entrada Sugerida:</b> Cantos Asiáticos FT
⛳️ <b>+{bd_canto_05} - Green ✅✅✅</b>
⛳️ <b>+{bd_canto_01}.0 - Reembolso 🔁🔁🔁</b>
'''
                        bot.edit_message_text(text=correcao_clFT, chat_id=chat_id, message_id=bd_msg_id,parse_mode="HTML")
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual}, {'$set': {'green': resultados_bd['green'] + 1}})
                        time.sleep(2)
                        partida_corrigida_clht = f'Over 0.5 FT - {item} | {bd_homeTeam} - {bd_awayTeam} | Green ✅✅✅ - Reembolso 🔁🔁🔁'
                        print(partida_corrigida_clht.center(150, " "))
                        collection_cantolimiteFT.delete_many(filter)

                    if (corners_home1 + corners_away1) > bd_canto_01:
                        correcao_clFT = f'''<b>🚨 Futebol Stats 🚨</b> 
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_home}

<b>Estratégia: ⛳️ {bd_estrategia} ⛳️</b>
<b>Entrada Sugerida:</b> Cantos Asiáticos FT
⛳️ <b>+{bd_canto_05} - Green ✅✅✅</b>
⛳️ <b>+{bd_canto_01}.0 - Green ✅✅✅</b>
                    '''
                        bot.edit_message_text(text=correcao_clFT, chat_id=chat_id, message_id=bd_msg_id,parse_mode="HTML")
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'green': resultados_bd['green'] + 1}})
                        time.sleep(2)
                        partida_corrigida_clft = f'Over 0.5 FT - {item} | {bd_homeTeam} - {bd_awayTeam} | Green ✅✅✅ - Green ✅✅✅'
                        print(partida_corrigida_clft.center(150, " "))
                        collection_cantolimiteFT.delete_many(filter)

                    if (corners_home1 + corners_away1) < bd_canto_05:
                        correcao_clFT = f'''             
🏟 <b>Jogo:</b> {bd_homeTeam} x {bd_awayTeam}
🏆 <b>Competição:</b> {bd_league}
🆚 <b>Placar:</b> {bd_homeTeamScore} x {bd_awayTeamScore}
⏰ <b>Tempo da Partida:</b> {bd_minute}'

<b>Estatísticas até os {bd_minute}' minutos</b>
⛳️ Escanteios: {bd_corners_home} - {bd_corners_away}
🔥 Ataques perigosos: {bd_dangerousAttacks_home} - {bd_dangerousAttacks_away}
🧨 APPM: {bd_appm1_home:.2f} - {bd_appm1_away:.2f}
🎯 Chutes no gol: {bd_shotsOngoal_home} - {bd_shotsOngoal_away}
💥 Chutes fora do gol: {bd_shotsOffgoal_home} - {bd_shotsOffgoal_home}

<b>Estratégia: ⛳️ {bd_estrategia} ⛳️</b>
<b>Entrada Sugerida:</b> Cantos Asiáticos HT 
⛳️ <b>+{bd_canto_05} - Red ❌❌❌️</b>
⛳️ <b>+{bd_canto_01}.0 - Red ❌❌❌️</b>
'''
                        bot.edit_message_text(text=correcao_clFT, chat_id=chat_id, message_id=bd_msg_id,parse_mode="HTML")
                        resultados_bd = collection_resultadoDiario.find_one({'data': data_atual})
                        collection_resultadoDiario.update_one({'data': data_atual},{'$set': {'red': resultados_bd['red'] + 1}})
                        time.sleep(2)
                        partida_corrigida_clft = f'Over 0.5 FT - {item} | {bd_homeTeam} - {bd_awayTeam} | Red ❌❌❌️ - Red ❌❌❌️'
                        print(partida_corrigida_clft.center(150, " "))
                        collection_cantolimiteFT.delete_many(filter)
            else:
                print("RETORNO DA API FALHOU AGUARDANDO 60 SEGUNDOS PARA TENTAR NOVAMENTE")
                time.sleep(60)

        print("")
        lista_correcao = " Processos de analise e correções encerradas, proxima analise em 60 segundos "
        print(lista_correcao.center(150, "="))
        print("")
        time.sleep(60)
        os.system("cls")

    except:
      pass
