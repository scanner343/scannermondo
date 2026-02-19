import os
import json
import requests
import time
import plistlib
import re
import copy 
import random 
import functools
from playwright.sync_api import sync_playwright

# FORZA PYTHON A SCRIVERE I LOG IN TEMPO REALE SENZA ATTENDERE LA FINE DELLO SCRIPT
print = functools.partial(print, flush=True)

# =======================================================
# --- CONFIGURAZIONE MONDO 343 ---
SERVER_ID = "LKWorldServer-RE-IT-7"
WORLD_ID = "343"
WORLD_NAME = "Italia VII" 
BACKEND_URL = "https://backend2.lordsandknights.com"
FILE_DATABASE = "database_mondo_343.json"
FILE_HISTORY = "cronologia_343.json"
# =======================================================

def send_telegram_alert(world_name):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id: 
        print("⚠️ [SISTEMA] Credenziali Telegram mancanti, salto l'invio dell'allarme.")
        return
        
    messaggio = f"Capo, il bot non riesce a loggarsi nel mondo '{world_name}' quindi probabilmente è stato bannato, controlla."
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try: 
        requests.post(url, json={"chat_id": chat_id, "text": messaggio})
        print("📲 [TELEGRAM] Messaggio di allarme inviato con successo!")
    except: 
        print("⚠️ [TELEGRAM] Errore di connessione con i server di Telegram.")

class RePanzaClient:
    def __init__(self, cookies, user_agent):
        self.cookies = cookies
        self.user_agent = user_agent

    @staticmethod
    def auto_login(email, password):
        print("\n🔑 [LOGIN] Inizio procedura di Login Sicuro con Playwright...")
        
        for tentativo in range(1, 4):
            print(f"   🔄 [TENTATIVO {tentativo}/3] Avvio browser Chrome invisibile...")
            with sync_playwright() as p:
                ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                args = ['--disable-blink-features=AutomationControlled', '--no-sandbox']
                browser = p.chromium.launch(headless=True, args=args)
                
                context = browser.new_context(
                    user_agent=ua,
                    locale='it-IT',
                    timezone_id='Europe/Rome'
                )
                page = context.new_page()
                
                popup_gestito = False
                
                try:
                    print("   [LOGIN] Mi collego alla homepage di Lords & Knights...")
                    page.goto("https://www.lordsandknights.com/", timeout=120000)
                    time.sleep(random.uniform(1.5, 3.0))
                    
                    try: page.wait_for_selector('input[placeholder="Email"]', state="visible", timeout=10000)
                    except: print("   [LOGIN] Attesa campo email prolungata...")

                    print("   [LOGIN] Digito le credenziali segrete come un umano...")
                    page.type('input[placeholder="Email"]', email, delay=random.randint(50, 150))
                    time.sleep(random.uniform(0.3, 0.8))
                    page.type('input[placeholder="Password"]', password, delay=random.randint(50, 150))
                    time.sleep(random.uniform(0.5, 1.2))
                    print("   [LOGIN] Clicco sul tasto di accesso...")
                    
                    page.locator('button:has-text("ACCESSO"), button:has-text("LOG IN")').first.click()
                    
                    selector_mondo = page.locator(f".button-game-world--title:has-text('{WORLD_NAME}')").first
                    selector_ok = page.locator("button:has-text('OK')")
                    
                    print(f"   [LOGIN] ⏳ Attesa comparsa del mondo '{WORLD_NAME}' (Max 1 minuto)...")
                    start_time = time.time()
                    while time.time() - start_time < 60:
                        
                        if selector_ok.is_visible(): 
                            print("   ⚠️ [LOGIN] Popup OK trovato! Lo premo e attendo 30 secondi esatti...")
                            try: 
                                selector_ok.click()
                                time.sleep(30)
                                popup_gestito = True
                            except: pass
                            
                            cookies = context.cookies()
                            if any(c['name'] == 'sessionID' for c in cookies):
                                print(f"✅ [LOGIN] Entrato dopo i 30 secondi di attesa! Sessione rubata al tentativo {tentativo}.")
                                final_cookies = context.cookies()
                                browser.close()
                                return RePanzaClient(final_cookies, ua)
                            else:
                                print(f"   ❌ [LOGIN] Passati i 30 secondi, il pacchetto sessionID non c'è. Interrompo il tentativo {tentativo}.")
                                break 

                        if selector_mondo.is_visible():
                            try: 
                                print(f"   [LOGIN] Tasto del mondo trovato! Entro in {WORLD_NAME}...")
                                time.sleep(random.uniform(0.8, 1.5))
                                selector_mondo.click(force=True)
                            except: pass
                        
                        cookies = context.cookies()
                        if any(c['name'] == 'sessionID' for c in cookies):
                            print(f"✅ [LOGIN] Successo al tentativo {tentativo}! Sessione 'sessionID' rubata con successo al server.")
                            final_cookies = context.cookies()
                            browser.close()
                            return RePanzaClient(final_cookies, ua)
                        time.sleep(random.uniform(0.8, 1.3))
                    
                    if popup_gestito:
                        pass
                    else:
                        print(f"🛑 [LOGIN] Timeout: È passato 1 minuto e il gioco non mi ha fatto entrare al tentativo {tentativo}.")
                    
                    try: page.screenshot(path=f"debug_login_error_t{tentativo}.png", full_page=True)
                    except: pass

                except Exception as e:
                    print(f"⚠️ [LOGIN] Errore critico durante la navigazione: {e}")
                    try: page.screenshot(path=f"debug_login_error_t{tentativo}.png", full_page=True)
                    except: pass
                
                browser.close()
                if tentativo < 3:
                    print("   ⏳ Riposo qualche secondo prima del prossimo tentativo per non insospettire i server...")
                    time.sleep(random.uniform(3.0, 5.0))

        print("❌ [LOGIN] TUTTI I 3 TENTATIVI SONO FALLITI. ABBANDONO.")
        return None

def fetch_ranking(client, missing_ids="ALL"):
    session = requests.Session()
    for cookie in client.cookies: session.cookies.set(cookie['name'], cookie['value'])
    session.headers.update({
        'User-Agent': client.user_agent,
        'Accept': 'application/x-bplist',
        'Content-Type': 'application/x-www-form-urlencoded',
        'XYClient-Client': 'lk_b_3',
        'XYClient-Loginclient': 'Chrome',
        'XYClient-Platform': 'browser',
        'Origin': 'https://www.lordsandknights.com',
        'Referer': 'https://www.lordsandknights.com/'
    })

    url = f"{BACKEND_URL}/XYRALITY/WebObjects/{SERVER_ID}.woa/wa/QueryAction/playerRanks"
    all_players = {}
    offset = 0
    
    full_scan = (missing_ids == "ALL")
    if not full_scan and not missing_ids:
        return all_players 

    target_set = set() if full_scan else set(missing_ids)
    mod_text = "COMPLETA" if full_scan else f"MIRATA ({len(target_set)} ID mancanti)"
    print(f"\n🚀 [CLASSIFICA] Scansione Giocatori. Modalità: {mod_text}")

    while True:
        payload = {'offset': str(offset), 'limit': '100', 'type': '(player_rank)', 'worldId': WORLD_ID}
        try:
            print(f"   📖 Leggo Pagina Giocatori {(offset//100) + 1}...")
            res = session.post(url, data=payload, timeout=20)
            if res.status_code != 200: break
            data = plistlib.loads(res.content)
            players = data.get('playerRanks', []) or data.get('rows', [])
            if not players: break
            
            for p in players:
                pid = int(p.get('playerID') or p.get('p') or p.get('id') or 0)
                name = p.get('nick') or p.get('n') or p.get('name') or ""
                if pid: 
                    all_players[pid] = name
                    if not full_scan and pid in target_set:
                        target_set.remove(pid)
                        
            if not full_scan and len(target_set) == 0:
                print(f"   🎯 BINGO! Trovati tutti i giocatori cercati. Interrompo la scansione in anticipo.")
                break
                
            offset += 100
            time.sleep(random.uniform(0.4, 1.1))
        except: break
        
    print(f"✅ [CLASSIFICA] Finito. Estratti {len(all_players)} nomi.")
    return all_players

def fetch_alliance_ranking(client, missing_ids="ALL"):
    session = requests.Session()
    for cookie in client.cookies: session.cookies.set(cookie['name'], cookie['value'])
    session.headers.update({
        'User-Agent': client.user_agent,
        'Accept': 'application/x-bplist',
        'Content-Type': 'application/x-www-form-urlencoded',
        'XYClient-Client': 'lk_b_3',
        'XYClient-Loginclient': 'Chrome',
        'XYClient-Platform': 'browser',
        'Origin': 'https://www.lordsandknights.com',
        'Referer': 'https://www.lordsandknights.com/'
    })

    url = f"{BACKEND_URL}/XYRALITY/WebObjects/{SERVER_ID}.woa/wa/QueryAction/allianceRanks"
    all_alliances = {}
    offset = 0
    
    full_scan = (missing_ids == "ALL")
    if not full_scan and not missing_ids:
        return all_alliances

    target_set = set() if full_scan else set(missing_ids)
    mod_text = "COMPLETA" if full_scan else f"MIRATA ({len(target_set)} ID mancanti)"
    print(f"\n🚀 [ALLEANZE] Scansione Alleanze. Modalità: {mod_text}")

    while True:
        payload = {'offset': str(offset), 'limit': '100', 'type': '(alliance_rank)', 'worldId': WORLD_ID}
        try:
            print(f"   🛡️ Leggo Pagina Alleanze {(offset//100) + 1}...")
            res = session.post(url, data=payload, timeout=20)
            if res.status_code != 200: break
            data = plistlib.loads(res.content)
            alliances = data.get('allianceRanks', []) or data.get('rows', [])
            if not alliances: break
            
            for a in alliances:
                aid = int(a.get('allianceID') or a.get('a') or a.get('id') or 0)
                name = a.get('name') or a.get('n') or ""
                if aid: 
                    all_alliances[aid] = name
                    if not full_scan and aid in target_set:
                        target_set.remove(aid)
                        
            if not full_scan and len(target_set) == 0:
                print(f"   🎯 BINGO! Trovate tutte le alleanze cercate. Interrompo.")
                break
                
            offset += 100
            time.sleep(random.uniform(0.4, 1.1))
        except: break
        
    print(f"✅ [ALLEANZE] Finito. Estratti {len(all_alliances)} nomi.")
    return all_alliances

def process_tile_public(x, y, session, tmp_map):
    url = f"{BACKEND_URL}/maps/{SERVER_ID}/{x}_{y}.jtile"
    try:
        time.sleep(random.uniform(0.05, 0.15))
        response = session.get(url, timeout=10)
        if response.status_code != 200: return 0
        
        testo_pulito = response.text.replace(" ", "").replace("\n", "")
        if "callback_politicalmap({})" in testo_pulito:
            return 0
        
        start = response.text.find('(')
        end = response.text.rfind(')')
        
        count = 0
        if start != -1 and end != -1:
            data = json.loads(response.text[start+1:end])
            if 'habitatArray' in data:
                for h in data['habitatArray']:
                    count += 1
                    pid = int(h.get('playerid') or 0)
                    aid = int(h.get('allianceid') or 0)
                    pts = int(h.get('points') or 0)
                    htype = int(h.get('habitattype') or 0)
                    
                    key = f"{h['mapx']}_{h['mapy']}"
                    
                    if key in tmp_map:
                        tmp_map[key].update({
                            'p': pid,
                            'a': aid,
                            'n': h.get('name', ''),
                            'pt': pts,
                            't': htype,
                            'd': int(time.time())
                        })
                    else:
                        tmp_map[key] = {
                            'p': pid, 'pn': "Sconosciuto",
                            'a': aid, 'an': "",
                            'n': h.get('name', ''),
                            'x': int(h['mapx']), 'y': int(h['mapy']),
                            'pt': pts, 't': htype,
                            'd': int(time.time())
                        }
        return count
    except Exception as e: 
        print(f"   ⚠️ ERRORE PYTHON al quadrante {x}_{y}: {e}")
    return 0

def extract_hidden_ids(node, known_map, found_set):
    if isinstance(node, dict):
        hx = node.get('x') or node.get('mapX') or node.get('mapx')
        hy = node.get('y') or node.get('mapY') or node.get('mapy')
        
        if hx is not None and hy is not None:
            try:
                hid = node.get('id') or node.get('habitatID') or node.get('primaryKey')
                if hid and str(hid).isdigit():
                    key = f"{int(hx)}_{int(hy)}"
                    if key in known_map:
                        known_map[key]['id_habitat'] = int(hid)
                        found_set.add(key)
            except: pass
        
        for k, v in node.items():
            if isinstance(v, dict):
                sub_hx = v.get('x') or v.get('mapX') or v.get('mapx')
                sub_hy = v.get('y') or v.get('mapY') or v.get('mapy')
                if sub_hx is not None and sub_hy is not None:
                    try:
                        sub_hid = v.get('id') or v.get('primaryKey')
                        if not sub_hid or not str(sub_hid).isdigit():
                            sub_hid = k 
                        
                        if sub_hid and str(sub_hid).isdigit(): 
                            key = f"{int(sub_hx)}_{int(sub_hy)}"
                            if key in known_map:
                                known_map[key]['id_habitat'] = int(sub_hid)
                                found_set.add(key)
                    except: pass
            extract_hidden_ids(v, known_map, found_set)
            
    elif isinstance(node, list):
        last_hx, last_hy = None, None
        for item in node:
            if isinstance(item, dict):
                hx = item.get('x') or item.get('mapX') or item.get('mapx')
                hy = item.get('y') or item.get('mapY') or item.get('mapy')
                
                if hx is not None and hy is not None:
                    last_hx, last_hy = hx, hy
                
                hid = item.get('id') or item.get('habitatID') or item.get('primaryKey')
                if hid and str(hid).isdigit():
                    use_hx = hx if hx is not None else last_hx
                    use_hy = hy if hy is not None else last_hy
                    
                    if use_hx is not None and use_hy is not None:
                        key = f"{int(use_hx)}_{int(use_hy)}"
                        if key in known_map:
                            known_map[key]['id_habitat'] = int(hid)
                            found_set.add(key)
        
        for item in node:
            extract_hidden_ids(item, known_map, found_set)

def enrich_with_habitat_ids(client, temp_map, castelli_senza_id):
    print("\n🔑 [ID SEGRETI] Avvio estrazione HabitatID mancanti tramite chiamate MapAction...")
    session = requests.Session()
    for cookie in client.cookies: session.cookies.set(cookie['name'], cookie['value'])
    
    session.headers.update({
        'User-Agent': client.user_agent,
        'Accept': 'application/x-bplist',
        'Content-Type': 'application/x-www-form-urlencoded',
        'XYClient-Client': 'lk_b_3',
        'XYClient-Loginclient': 'Chrome',
        'XYClient-Loginclientversion': '10.8.0',
        'XYClient-Platform': 'browser',
        'XYClient-Capabilities': 'base,fortress,city,parti%D0%B0l%CE%A4ran%D1%95its,starterpack,requestInformation,partialUpdate,regions,metropolis',
        'Origin': 'https://www.lordsandknights.com',
        'Referer': 'https://www.lordsandknights.com/'
    })
    
    zone_da_scaricare = set()
    for entry in castelli_senza_id.values():
        zone_da_scaricare.add((entry['x'] // 32, entry['y'] // 32))
    
    print(f"🗺️ [ID SEGRETI] Ho raggruppato i nuovi castelli in {len(zone_da_scaricare)} quadranti.")
    habitat_trovati = 0
    
    for count, (tx, ty) in enumerate(zone_da_scaricare, 1):
        url = f"{BACKEND_URL}/XYRALITY/WebObjects/{SERVER_ID}.woa/wa/MapAction/map"
        payload = {
            'mapX': str(tx*32), 'mapY': str(ty*32), 
            'mapWidth': '32', 'mapHeight': '32', 
            'worldId': WORLD_ID, 'logoutUrl': 'http://lordsandknights.com/'
        }
        try:
            print(f"   🕵️‍♂️ [{count}/{len(zone_da_scaricare)}] Faccio una richiesta privata per il quadrante {tx}_{ty}...")
            time.sleep(random.uniform(1.5, 3.5)) 
            res = session.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                data = plistlib.loads(res.content)
                found_in_this_request = set()
                extract_hidden_ids(data, temp_map, found_in_this_request)
                habitat_trovati += len(found_in_this_request)
                print(f"      ✔️ Estratti {len(found_in_this_request)} chiavi primarie valide!")
            else:
                print(f"      ❌ Errore HTTP {res.status_code} dal server.")
        except Exception as e: 
            print(f"      ❌ Errore di decodifica durante l'ispezione: {e}")

    print(f"🎯 [ID SEGRETI] Finito! Aggiunti {habitat_trovati} nuovi HabitatID nel database.")

def enrich_db_with_names(db, player_map, alliance_map):
    print("\n📝 [UNIONE DATI] Sto associando i nomi alle coordinate grezze...")
    count_updated = 0
    for key, record in db.items():
        pid = record.get('p')
        
        # --- FIX CASTELLI FANTASMA ---
        if pid and pid != 0:
            nome_nuovo = player_map.get(pid, "Sconosciuto")
            if 'pn' not in record or record['pn'] != nome_nuovo:
                 record['pn'] = nome_nuovo
                 count_updated += 1
        else:
            if record.get('pn') != "Sconosciuto":
                record['pn'] = "Sconosciuto"
                count_updated += 1
                 
        aid = record.get('a')
        if aid and aid != 0:
            nome_alleanza = alliance_map.get(aid, "")
            if 'an' not in record or record['an'] != nome_alleanza:
                 record['an'] = nome_alleanza
        else:
            if record.get('an') != "":
                record['an'] = ""

    print(f"♻️ [UNIONE DATI] Perfetto, i nomi di giocatori e alleanze sono stati applicati/puliti su {count_updated} castelli nel database.")
    return db

def run_inactivity_check(data):
    print("\n⏳ [INATTIVITÀ] Calcolo chi sta giocando e chi sta dormendo (Analisi Globale Account)...")
    
    player_last_active = {}
    
    # FASE 1: Trovo l'ultimo segno di vita per ogni giocatore
    for key, h in data.items():
        p = h.get('p')
        if not p or p == 0: continue
        
        firma = f"{h.get('pn', 'Sconosciuto')}|{h.get('a', 0)}|{h['n']}|{h['pt']}"
        h['d'] = int(h['d'])
        
        if 'u' not in h or h.get('f') != firma:
            ultimo_movimento = h['d']
        else:
            ultimo_movimento = int(h['u'])
            
        if p not in player_last_active or ultimo_movimento > player_last_active[p]:
            player_last_active[p] = ultimo_movimento

    # FASE 2: Applico lo stato di inattività a tutti i castelli
    inattivi_trovati = 0
    for key, h in data.items():
        p = h.get('p')
        if not p or p == 0: continue
        
        firma = f"{h.get('pn', 'Sconosciuto')}|{h.get('a', 0)}|{h['n']}|{h['pt']}"
        
        if 'u' not in h or h.get('f') != firma:
            h['u'] = h['d']
            h['f'] = firma
        
        secondi_fermo_giocatore = h['d'] - player_last_active.get(p, h['d'])
        
        if secondi_fermo_giocatore >= 86400: 
            h['i'] = True
            inattivi_trovati += 1
        else:
            h['i'] = False
            
    print(f"🛌 [INATTIVITÀ] Analisi completata: {inattivi_trovati} castelli appartengono a giocatori inattivi da più di 24 ore.")
    return data

def run_history_check(old_db_list, new_db_list, history_file):
    print("\n🕰️ [CRONOLOGIA] Verifico chi ha cambiato bandiera o nome...")
    
    history = {}
    needs_saving = False  
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f: 
                loaded_data = json.load(f)
                if isinstance(loaded_data, dict):
                    history = loaded_data
                elif isinstance(loaded_data, list):
                    print("   🔄 [MIGRAZIONE] Rilevato vecchio formato lista. Converto in cartelle anagrafiche...")
                    for ev in loaded_data:
                        pid = str(ev.get('p'))
                        if pid not in history: history[pid] = []
                        history[pid].append(ev)
                    needs_saving = True 
        except: pass

    last_known = {}
    for h in old_db_list:
        pid = h.get('p')
        if pid and pid != 0:
            if pid not in last_known:
                last_known[pid] = {'n': h.get('pn', 'Sconosciuto'), 'a': h.get('a', 0), 'an': h.get('an', '')}

    current_known = {}
    for h in new_db_list:
        pid = h.get('p')
        if pid and pid != 0:
            if pid not in current_known:
                current_known[pid] = {'n': h.get('pn', 'Sconosciuto'), 'a': h.get('a', 0), 'an': h.get('an', '')}

    now = int(time.time())
    new_events_count = 0

    for pid, new_data in current_known.items():
        if pid in last_known:
            old_data = last_known[pid]
            
            old_name = old_data['n']
            new_name = new_data['n']
            name_changed = (old_name and old_name != "Sconosciuto" and new_name and new_name != "Sconosciuto" and old_name != new_name)
            
            old_ally = old_data['a']
            new_ally = new_data['a']
            ally_changed = (old_ally != new_ally)

            event_to_add = None

            if name_changed and ally_changed:
                event_to_add = {
                    "type": "name_and_alliance", 
                    "p": pid, 
                    "old_name": old_name, 
                    "new_name": new_name, 
                    "old_ally": old_ally, 
                    "new_ally": new_ally, 
                    "old_ally_name": old_data['an'], 
                    "new_ally_name": new_data['an'], 
                    "d": now
                }
                print(f"   📜 [EVENTO DOPPIO] Il Giocatore {pid} ha cambiato NOME (da '{old_name}' a '{new_name}') e ALLEANZA (da {old_ally} a {new_ally})")
            
            elif name_changed:
                event_to_add = {"type": "name", "p": pid, "old": old_name, "new": new_name, "d": now}
                print(f"   📜 [EVENTO] Il Giocatore {pid} ha cambiato nome da '{old_name}' a '{new_name}'")
            
            elif ally_changed:
                event_to_add = {
                    "type": "alliance", "p": pid, "old": old_ally, "new": new_ally, 
                    "old_name": old_data['an'], "new_name": new_data['an'], "d": now
                }
                print(f"   📜 [EVENTO] Il Giocatore {pid} ha cambiato alleanza da {old_ally} a {new_ally}")
            
            if event_to_add:
                str_pid = str(pid)
                if str_pid not in history:
                    history[str_pid] = []
                history[str_pid].append(event_to_add)
                
                if len(history[str_pid]) > 50:
                    history[str_pid] = history[str_pid][-50:]
                
                new_events_count += 1
                needs_saving = True

    if needs_saving:
        if new_events_count > 0:
            print(f"📥 [CRONOLOGIA] Salvo {new_events_count} nuovi eventi nel file storico.")
        else:
            print("💾 [CRONOLOGIA] Salvo la conversione del file storico (nessun nuovo evento aggiunto questa volta).")
            
        with open(history_file, 'w', encoding='utf-8') as f: 
            json.dump(history, f, indent=2)
    else:
        print("💤 [CRONOLOGIA] Nessun cambiamento rilevato tra i giocatori.")


def run_unified_scanner():
    print("=====================================================")
    print("🚀 FASE 1: INIZIALIZZAZIONE E MEMORIA")
    print("=====================================================")
    
    if not os.path.exists(FILE_DATABASE):
        with open(FILE_DATABASE, 'w') as f: json.dump([], f)
        
    temp_map = {}
    old_known_players = {}
    old_known_alliances = {}
    
    with open(FILE_DATABASE, 'r') as f:
        print(f"📥 Sto caricando il vecchio database '{FILE_DATABASE}' nella memoria temporanea e pulendo eventuali errori...")
        for entry in json.load(f): 
            
            # --- ANTIVIRUS ID ---
            if 'id_habitat' in entry:
                if not str(entry['id_habitat']).isdigit():
                    del entry['id_habitat'] 
                else:
                    entry['id_habitat'] = int(entry['id_habitat'])

            temp_map[f"{entry['x']}_{entry['y']}"] = entry
            
            if entry.get('p') and entry.get('pn') and entry.get('pn') != "Sconosciuto":
                old_known_players[entry['p']] = entry['pn']
            if entry.get('a') and entry.get('an'):
                old_known_alliances[entry['a']] = entry['an']
                
    old_db_list = copy.deepcopy(list(temp_map.values()))
    print(f"📸 Ho scattato la 'fotografia' del database vecchio ({len(temp_map)} castelli noti).")

    print("\n=====================================================")
    print("🌍 FASE 2: SCANSIONE MAPPA PUBBLICA (Modo Stealth)")
    print("=====================================================")
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    })
    
    punti_caldi = {}
    cache_conteggi_tile = {}
    
    for entry in temp_map.values():
        tx, ty = entry['x'] // 32, entry['y'] // 32
        chiave_tile = f"{tx}_{ty}"
        punti_caldi[chiave_tile] = (tx, ty)
        cache_conteggi_tile[chiave_tile] = cache_conteggi_tile.get(chiave_tile, 0) + 1

    print(f"🔥 Prima passata: Aggiorno al volo {len(punti_caldi)} quadranti caldi già conosciuti...")
    for tx, ty in punti_caldi.values():
        num = process_tile_public(tx, ty, session, temp_map)
        cache_conteggi_tile[f"{tx}_{ty}"] = num 
        if num > 0:
            print(f"   📍 [AGGIORNAMENTO] Quadrante {tx}_{ty}: {num} castelli presenti.")
    print("✅ Punti caldi aggiornati.")

    centerX, centerY = 512, 512
    if temp_map:
        vals = list(temp_map.values())
        if vals:
            centerX = sum(e['x']//32 for e in vals) // len(vals)
            centerY = sum(e['y']//32 for e in vals) // len(vals)
    print(f"🚁 Avvio espansione a spirale dal centro di massa: Quadrante ({centerX}, {centerY})")

    vuoti = 0
    for r in range(1, 150):
        trovato = False
        castelli_giro = 0
        xMin, xMax = centerX - r, centerX + r
        yMin, yMax = centerY - r, centerY + r
        punti = []
        
        for i in range(xMin, xMax + 1): 
            if 0 <= i <= 600:
                if 0 <= yMin <= 600: punti.append((i, yMin))
                if 0 <= yMax <= 600: punti.append((i, yMax))
        for j in range(yMin + 1, yMax): 
            if 0 <= j <= 600:
                if 0 <= xMin <= 600: punti.append((xMin, j))
                if 0 <= xMax <= 600: punti.append((xMax, j))
        
        punti = list(set(punti))
        print(f"⭕ Anello {r}/150: Controllo {len(punti)} quadranti periferici...")
        
        for px, py in punti:
            chiave_quadrante = f"{px}_{py}"
            
            if chiave_quadrante in punti_caldi:
                num = cache_conteggi_tile.get(chiave_quadrante, 0)
                trovato = True
                castelli_giro += num
                if num > 0:
                    print(f"   💾 [MEMORIA] Quadrante {px}_{py}: Ci sono {num} castelli (Già noti).")
            else:
                num = process_tile_public(px, py, session, temp_map)
                if num > 0: 
                    trovato = True
                    print(f"   ✨ [NUOVO] Quadrante {px}_{py}: Trovati {num} castelli!")
                    castelli_giro += num
                punti_caldi[chiave_quadrante] = (px, py)
                cache_conteggi_tile[chiave_quadrante] = num
        
        if trovato: 
            print(f"   🏰 Anello {r} completato! Totale castelli attivi in questa zona: {castelli_giro}. Azzero vuoti.")
            vuoti = 0
        else: 
            vuoti += 1
            print(f"   🏜️ Anello {r} deserto. Giri a vuoto consecutivi: {vuoti}/3")
            
        if vuoti >=3: 
            print(f"🛑 Mi fermo: Ho scansionato 3 anelli vuoti, la mappa è sicuramente finita.")
            break

    missing_p = set()
    missing_a = set()
    for entry in temp_map.values():
        p = entry.get('p', 0)
        a = entry.get('a', 0)
        if p != 0 and p not in old_known_players: missing_p.add(p)
        if a != 0 and a not in old_known_alliances: missing_a.add(a)

    castelli_senza_id = {k: v for k, v in temp_map.items() if 'id_habitat' not in v}
    is_full_scan = (len(old_db_list) == 0)

    if not is_full_scan and not missing_p and not missing_a and not castelli_senza_id:
        print("\n⚡ NESSUN NUOVO GIOCATORE O CASTELLO RILEVATO.")
        print("⏩ Salto completamente la Fase di Login e le Classifiche per risparmiare tempo!")
        temp_map = enrich_db_with_names(temp_map, old_known_players, old_known_alliances)
        
    else:
        print("\n=====================================================")
        print("🔐 FASE 3: ACCESSO GIOCO E RICERCA DATI SEGRETI")
        print("=====================================================")
        EMAIL = os.getenv("LK_EMAIL")
        PASSWORD = os.getenv("LK_PASSWORD")
        
        client = None
        if EMAIL and PASSWORD:
            client = RePanzaClient.auto_login(EMAIL, PASSWORD)
        else:
            print("⚠️ LK_EMAIL o LK_PASSWORD mancanti nei Secrets di GitHub. Salto il login.")
        
        if client:
            p_arg = "ALL" if is_full_scan else missing_p
            a_arg = "ALL" if is_full_scan else missing_a
            
            new_players = fetch_ranking(client, p_arg)
            new_alliances = fetch_alliance_ranking(client, a_arg)
            
            combined_players = {**old_known_players, **new_players}
            combined_alliances = {**old_known_alliances, **new_alliances}
            
            temp_map = enrich_db_with_names(temp_map, combined_players, combined_alliances)
            
            if castelli_senza_id:
                print(f"\n⚠️ Ho rilevato {len(castelli_senza_id)} nuovi castelli a cui manca la chiave primaria.")
                enrich_with_habitat_ids(client, temp_map, castelli_senza_id)
        else:
            print("❌ Login non riuscito. Non posso né scaricare i nomi, né cercare i nuovi ID Habitat.")
            send_telegram_alert(WORLD_NAME)

    print("\n=====================================================")
    print("💾 FASE 4: ELABORAZIONI FINALI E SALVATAGGIO")
    print("=====================================================")
    
    temp_map = run_inactivity_check(temp_map)
    new_db_list = list(temp_map.values())
    run_history_check(old_db_list, new_db_list, FILE_HISTORY)
    
    print("🧹 Pulizia database: Elimino i castelli spariti dalla mappa da più di 3 giorni...")
    final_list = [v for v in temp_map.values() if v['d'] > (time.time() - 259200)]
    
    print(f"📦 Compressione e scrittura nel file {FILE_DATABASE}...")
    with open(FILE_DATABASE, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, indent=2, ensure_ascii=False)
    
    print("\n=====================================================")
    print(f"✅ OPERAZIONE COMPLETATA! Database aggiornato e chiuso. ({len(final_list)} castelli in totale)")
    print("=====================================================")

if __name__ == "__main__":
    run_unified_scanner()
