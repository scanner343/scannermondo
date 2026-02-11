const fs = require('fs');

// --- 🛠️ MODIFICA QUI IL NOME DEL FILE JSON ---
const FILE = 'database_mondo_343.json'; 
// ---------------------------------------------

console.log(`Aggiornamento inattività per: ${FILE}`);

try {
    if (!fs.existsSync(FILE)) {
        console.error(`File non trovato, ne creo uno vuoto.`);
        fs.writeFileSync(FILE, '[]');
    }

    const data = JSON.parse(fs.readFileSync(FILE, 'utf8'));
    const now = new Date();
    
    const finalData = data.map(h => {
        if (!h.p || h.p === 0) return h; 
        const firmaAttuale = `${h.n}|${h.pt}`;
        
        if (!h.u) { h.u = now.toISOString(); h.i = false; h.f = firmaAttuale; return h; }

        if (h.f !== firmaAttuale) {
            h.u = now.toISOString(); h.i = false; h.f = firmaAttuale;
        } else {
            const orePassate = (now - new Date(h.u)) / (1000 * 60 * 60);
            if (orePassate >= 24) { h.i = true; }
        }
        return h;
    });

    fs.writeFileSync(FILE, JSON.stringify(finalData, null, 2));
    console.log(`Storico aggiornato.`);

} catch (e) {
    console.error("Errore JS:", e.message);
    process.exit(1);
}
