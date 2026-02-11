const fs = require('fs');

// --- FILE CONFIGURAZIONE ---
const FILE = 'database_mondo_343.json';
// ---------------------------

console.log(`[JS] Avvio analisi inattività per: ${FILE}`);

try {
    if (!fs.existsSync(FILE)) {
        console.error(`❌ Errore: Il file ${FILE} non esiste!`);
        // Creiamo un file vuoto per evitare crash futuri
        fs.writeFileSync(FILE, '[]'); 
    }

    const data = JSON.parse(fs.readFileSync(FILE, 'utf8'));
    const now = new Date();
    
    // Creiamo una mappa dello stato attuale per confrontare i cambiamenti
    const finalData = data.map(h => {
        if (!h.p || h.p === 0) return h; // Salta castelli vuoti

        const firmaAttuale = `${h.n}|${h.pt}`;
        
        // Se è la prima volta che vede questo castello
        if (!h.u) {
            h.u = now.toISOString(); // ultima modifica
            h.i = false;             // inattivo
            h.f = firmaAttuale;      // firma
            return h;
        }

        // CONFRONTO: Se la firma è cambiata (punti o nome sono diversi)
        if (h.f !== firmaAttuale) {
            h.u = now.toISOString();
            h.i = false;
            h.f = firmaAttuale;
        } else {
            // Se la firma è identica, controlliamo se sono passate 24 ore
            const orePassate = (now - new Date(h.u)) / (1000 * 60 * 60);
            if (orePassate >= 24) {
                h.i = true; // Segna come inattivo
            }
        }

        return h;
    });

    fs.writeFileSync(FILE, JSON.stringify(finalData, null, 2));
    console.log(`✅ Database ${FILE} aggiornato con dati inattività.`);

} catch (e) {
    console.error("Errore JS:", e.message);
    process.exit(1);
}
