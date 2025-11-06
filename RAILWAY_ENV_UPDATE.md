# 🔑 Railway Environment Variables Update

## Aggiorna su Railway Dashboard

**URL**: https://railway.app/project/a89ce437-4398-43a9-9352-9dae7178545b

### Variabile da Aggiornare:

```bash
GEMINI_API_KEY=AIzaSyCBUfpJJmB_4aS5Pp71USIOoXfMnuUqNR8
```

### Steps:

1. Vai al progetto Railway
2. Clicca sul servizio backend
3. Vai su **Variables**
4. Aggiorna `GEMINI_API_KEY` con la nuova chiave
5. Il servizio si riavvierà automaticamente

---

## ✅ Modifiche Implementate

### Backend (`app.py`)
- ✅ Threshold cambiato da **0.75** a **0.65** (come nel notebook)
- ✅ Nuova chiave Gemini con fallback
- ✅ Best matching chunk salvato per ogni query
- ✅ Query più specifiche e challenging

### Frontend (`audit-ai/page.tsx`)
- ✅ Accordion con reasoning e best chunk
- ✅ Threshold display aggiornato a 65%
- ✅ Colori similarity: verde ≥65%, giallo <65%

---

## 🎯 Risultati Attesi

Dopo il deploy:
- ❌ Non più 100% coverage su pagine generiche
- ✅ Coverage realistico (30-70% tipico)
- ✅ Query più tecniche e specifiche
- ✅ Accordion espandibile con dettagli
- ✅ Best chunk visibile per ogni query

---

## 📊 Logica dal Notebook

Il sistema ora usa ESATTAMENTE la logica del notebook:
1. **Threshold 0.65** (non 0.75)
2. **Query specifiche** con facets reasoning
3. **Chunk tracking** per vedere quali chunk vengono usati
4. **Technical queries** invece di generiche

---

## 🚀 Test

Dopo l'aggiornamento, testa con:
- https://biolaser.it/crioterapia/
- https://francescoragusa.com/content-audit/

Dovresti vedere coverage più basso e realistico!
