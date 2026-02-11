<?php
// --- 🛠️ CONFIGURAZIONE DA MODIFICARE ---
$serverID = "LKWorldServer-RE-IT-7";        // 1. INSERISCI IL SERVER ID
$fileDatabase = 'database_mondo_343.json';  // 2. CAMBIA IL NUMERO DEL FILE JSON
$backendURL = "https://backend2.lordsandknights.com"; // 3. CONTROLLA IL BACKEND (http o https)
// ---------------------------------------

$tempMap = [];
$puntiCaldi = []; 

// Carica dati esistenti per velocizzare la scansione
if (file_exists($fileDatabase)) {
    $content = file_get_contents($fileDatabase);
    $currentData = json_decode($content, true);
    if (is_array($currentData)) {
        foreach ($currentData as $entry) {
            if (is_array($entry) && isset($entry['x'], $entry['y'])) {
                $tempMap[$entry['x'] . "_" . $entry['y']] = $entry;
                $puntiCaldi[floor($entry['x']/32) . "_" . floor($entry['y']/32)] = ['x' => floor($entry['x']/32), 'y' => floor($entry['y']/32)];
            }
        }
    }
}

echo "Avvio scansione per $serverID...\n";

// Fase 1: Aggiorna zone note
foreach ($puntiCaldi as $zona) { processTile($zona['x'], $zona['y'], $serverID, $tempMap, $backendURL); }

// Fase 2: Espansione a Spirale (Smart Scan)
$centerX = 500; $centerY = 500;
if (count($tempMap) > 0) {
    $sumX = 0; $sumY = 0;
    foreach ($tempMap as $h) { $sumX += floor($h['x']/32); $sumY += floor($h['y']/32); }
    $centerX = round($sumX / count($tempMap)); $centerY = round($sumY / count($tempMap));
}

$raggioMax = 150; $limiteVuoti = 10; $contatoreVuoti = 0;

for ($r = 0; $r <= $raggioMax; $r++) {
    $trovatoNuovo = false;
    $xMin = $centerX - $r; $xMax = $centerX + $r; $yMin = $centerY - $r; $yMax = $centerY + $r;
    $punti = [];
    for ($i = $xMin; $i <= $xMax; $i++) { $punti[] = [$i, $yMin]; $punti[] = [$i, $yMax]; }
    for ($j = $yMin + 1; $j < $yMax; $j++) { $punti[] = [$xMin, $j]; $punti[] = [$xMax, $j]; }
    
    foreach ($punti as $p) {
        if (isset($puntiCaldi[$p[0] . "_" . $p[1]])) continue;
        if (processTile($p[0], $p[1], $serverID, $tempMap, $backendURL)) { $trovatoNuovo = true; }
    }
    
    if ($trovatoNuovo) { $contatoreVuoti = 0; } else { $contatoreVuoti++; }
    if ($contatoreVuoti >= $limiteVuoti) { echo "Stop espansione: Trovato vuoto.\n"; break; }
}

// Pulizia dati vecchi (> 72h) e Salvataggio
$limite = time() - (72 * 3600);
$mappaPulita = array_filter($tempMap, function($e) use ($limite) { return !isset($e['d']) || $e['d'] > $limite; });
file_put_contents($fileDatabase, json_encode(array_values($mappaPulita), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
echo "Finito. Salvati " . count($mappaPulita) . " castelli in $fileDatabase.\n";

function processTile($x, $y, $sid, &$tmp, $bk) {
    $c = @file_get_contents("$bk/maps/$sid/{$x}_{$y}.jtile");
    if (!$c || $c === 'callback_politicalmap({})') return false; 
    if (preg_match('/\((.*)\)/s', $c, $m)) {
        $j = json_decode($m[1], true);
        if (isset($j['habitatArray']) && count($j['habitatArray']) > 0) {
            foreach ($j['habitatArray'] as $h) {
                $tmp[$h['mapx']."_".$h['mapy']] = [
                    'p' => (int)$h['playerid'], 'a' => (int)$h['allianceid'], 'n' => $h['name'] ?? '',
                    'x' => (int)$h['mapx'], 'y' => (int)$h['mapy'], 'pt'=> (int)$h['points'],
                    't' => (int)$h['habitattype'], 'd' => time()
                ];
            }
            return true;
        }
    }
    return false;
}
