<?php
// --- CONFIGURAZIONE MONDO 343 ---
$serverID = "LKWorldServer-RE-IT-7";
$fileDatabase = 'database_mondo_343.json';
$backendURL = "https://backend2.lordsandknights.com"; // Nota: HTTPS
// --------------------------------

$tempMap = [];
$puntiCaldi = []; 

// 1. Carica il database esistente (se c'è)
if (file_exists($fileDatabase)) {
    $content = file_get_contents($fileDatabase);
    $currentData = json_decode($content, true);
    
    if (is_array($currentData)) {
        foreach ($currentData as $entry) {
            if (is_array($entry) && isset($entry['x'], $entry['y'])) {
                $key = $entry['x'] . "_" . $entry['y'];
                $tempMap[$key] = $entry;
                // Calcola il "quadrante" (jtile) per sapere dove guardare
                $jtileX = floor($entry['x'] / 32); 
                $jtileY = floor($entry['y'] / 32);
                $puntiCaldi[$jtileX . "_" . $jtileY] = ['x' => $jtileX, 'y' => $jtileY];
            }
        }
    }
}

echo "Dati caricati. Analisi di " . count($puntiCaldi) . " quadranti conosciuti...\n";

// Fase 1: Aggiorna le zone dove sappiamo già che ci sono castelli
foreach ($puntiCaldi as $zona) {
    processTile($zona['x'], $zona['y'], $serverID, $tempMap, $backendURL);
}

// Fase 2: Espansione a Spirale (Cerca nuovi castelli vicino a quelli esistenti)
// Se il db è vuoto, parte dal centro (500, 500)
$centerX = 500; $centerY = 500;
if (count($tempMap) > 0) {
    $sumX = 0; $sumY = 0;
    foreach ($tempMap as $h) { $sumX += floor($h['x']/32); $sumY += floor($h['y']/32); }
    $centerX = round($sumX / count($tempMap));
    $centerY = round($sumY / count($tempMap));
}

// Raggio ridotto a 50 per sicurezza iniziale (puoi aumentarlo a 150 se stabile)
$raggioMax = 50; 
$limiteVuoti = 10; 
$contatoreVuoti = 0;

for ($r = 0; $r <= $raggioMax; $r++) {
    $trovatoNuovo = false;
    // Calcola il perimetro del quadrato (spirale)
    $xMin = $centerX - $r; $xMax = $centerX + $r;
    $yMin = $centerY - $r; $yMax = $centerY + $r;
    
    $punti = [];
    // Lati orizzontali
    for ($i = $xMin; $i <= $xMax; $i++) { $punti[] = [$i, $yMin]; $punti[] = [$i, $yMax]; }
    // Lati verticali
    for ($j = $yMin + 1; $j < $yMax; $j++) { $punti[] = [$xMin, $j]; $punti[] = [$xMax, $j]; }
    
    foreach ($punti as $p) {
        // Se abbiamo già fatto questo quadrante nella Fase 1, saltalo
        if (isset($puntiCaldi[$p[0] . "_" . $p[1]])) continue;
        
        // Scarica e analizza
        if (processTile($p[0], $p[1], $serverID, $tempMap, $backendURL)) {
            $trovatoNuovo = true;
        }
    }
    
    // Logica "Stop se vuoto": se facciamo 10 giri di spirale senza trovare nulla, ci fermiamo
    if ($trovatoNuovo) $contatoreVuoti = 0; else $contatoreVuoti++;
    if ($contatoreVuoti >= $limiteVuoti) {
        echo "Stop espansione: raggiunti limiti vuoti.\n";
        break;
    }
}

// Pulizia (rimuove castelli non aggiornati da 72h) e Salvataggio
$limite = time() - (72 * 3600);
$mappaPulita = array_filter($tempMap, function($e) use ($limite) { return !isset($e['d']) || $e['d'] > $limite; });

file_put_contents($fileDatabase, json_encode(array_values($mappaPulita), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
echo "Fine. Database locale aggiornato con " . count($mappaPulita) . " habitat.\n";

// --- FUNZIONI ---

function processTile($x, $y, $sid, &$tmp, $bk) {
    // URL della mappa
    $url = "$bk/maps/$sid/{$x}_{$y}.jtile";
    
    // USIAMO IL TUO CURL SPECIFICO
    $c = fetchWithCurl($url);
    
    // Controllo errori o mappa vuota
    if (!$c || $c === 'callback_politicalmap({})') return false; 
    
    // Parsing della risposta (JSON dentro parentesi)
    if (preg_match('/\((.*)\)/s', $c, $m)) {
        $j = json_decode($m[1], true);
        if (isset($j['habitatArray']) && count($j['habitatArray']) > 0) {
            foreach ($j['habitatArray'] as $h) {
                $tmp[$h['mapx']."_".$h['mapy']] = [
                    'p' => (int)$h['playerid'],
                    'a' => (int)$h['allianceid'],
                    'n' => $h['name'] ?? '',
                    'x' => (int)$h['mapx'],
                    'y' => (int)$h['mapy'],
                    'pt'=> (int)$h['points'],
                    't' => (int)$h['habitattype'],
                    'd' => time()
                ];
            }
            return true; // Trovato qualcosa!
        }
    }
    return false; // Nulla trovato
}

function fetchWithCurl($url) {
    $ch = curl_init();
    
    // Headers e Cookie presi ESATTAMENTE dal tuo curl
    $headers = [
        'Accept: application/x-bplist',
        'Accept-Language: it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection: keep-alive',
        'Origin: https://www.lordsandknights.com',
        'Referer: https://www.lordsandknights.com/',
        'Sec-Fetch-Dest: empty',
        'Sec-Fetch-Mode: cors',
        'Sec-Fetch-Site: same-site',
        'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'XY-Debug-ID: 572e207381 30fddc7c38 9f2ab14f4e 4b22a97c39',
        'XYClient-Capabilities: base%2Cfortress%2Ccity%2Cparti%D0%B0l%CE%A4ran%D1%95its%2Cstarterpack%2CrequestInformation%2CpartialUpdate%2Cregions%2Cmetropolis',
        'XYClient-Client: lk_b_3',
        'XYClient-LastRegionCycleID: 1770781904',
        'XYClient-Loginclient: Chrome',
        'XYClient-Loginclientversion: 10.8.0',
        'XYClient-PartialUpdateSince: 1770809388632',
        'XYClient-Platform: browser',
        'XYClient-PlatformLanguage: it',
        'sec-ch-ua: "Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile: ?0',
        'sec-ch-ua-platform: "Windows"'
    ];

    // Cookie di sessione
    $cookieStr = 'loginID=14289896; sessionID=da31938c-2503-4b4f-9388-1c3b3f27af98; playerID=6312';

    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_COOKIE, $cookieStr);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5); // Timeout basso per non bloccare
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); 
    curl_setopt($ch, CURLOPT_ENCODING, ''); // Accetta gzip se il server lo manda

    $result = curl_exec($ch);
    curl_close($ch);
    
    return $result;
}
?>
