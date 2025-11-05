# 🔗 Connettere GitHub Repository a Railway

## Stato Attuale

✅ **Git Remote aggiornato**: `https://github.com/Instilla-AI/mvp-ranksimulator.git`  
✅ **Codice pushato** su GitHub Instilla  
✅ **Railway CLI** loggato come `service@instilla.it`  
✅ **Progetto linkato**: ranksimulator  

⏳ **Manca**: Connettere il repository GitHub al servizio Railway

---

## Passo 1: Connetti Repository GitHub

### Via Railway Dashboard (Raccomandato)

1. **Vai al progetto Railway**
   - URL: https://railway.app/project/ranksimulator
   - O cerca "ranksimulator" nella dashboard

2. **Seleziona il servizio**
   - Click su **"mvp-ranksimulator"** service

3. **Vai alle Settings**
   - Click su **"Settings"** tab

4. **Connetti GitHub Repository**
   - Scroll fino a **"Source"** section
   - Click su **"Connect Repo"**
   - Seleziona **"Instilla-AI/mvp-ranksimulator"**
   - Branch: **"main"**
   - Click **"Connect"**

5. **Configura Deploy Trigger**
   - Assicurati che **"Deploy on Push"** sia abilitato
   - Questo farà deploy automatico ad ogni push su main

---

## Passo 2: Verifica Variabili d'Ambiente

Vai a **"Variables"** tab e verifica che ci siano:

```
✅ DATABASE_URL (reference da PostgreSQL)
✅ SECRET_KEY
✅ JWT_SECRET_KEY
✅ GEMINI_API_KEY
```

Se mancano, aggiungile:

```bash
SECRET_KEY=effdb741d8204075eacd74b48ab9d29ee1e3512dfc1b5bc26d04e1cbbb6b7f9d
JWT_SECRET_KEY=077bdb817eea258c68c26565d91612792a7d59f599e43e52b058c7c47137f07e
GEMINI_API_KEY=AIzaSyDD_lRQ99lz0R_J5_vOspGtF5ITA2DmRHM
```

---

## Passo 3: Trigger Deploy

Dopo aver connesso il repository, Railway farà automaticamente il deploy.

Oppure puoi triggare manualmente:

### Via Dashboard
1. Vai al servizio
2. Click su **"Deployments"** tab
3. Click su **"Deploy"** button

### Via CLI
```bash
railway up --detach
```

---

## Passo 4: Verifica Deploy

### Controlla i Log
```bash
railway logs
```

**Cerca questi messaggi di successo**:
```
Creating database tables...
✅ Database tables created!
Creating admin user...
✅ Admin user created!
   Email: ciccioragusa@gmail.com
   Password: 12345Aa!
```

### Testa l'API
```bash
# Test root endpoint (dovrebbe restituire JSON, non HTML)
curl https://mvp-ranksimulator-production.up.railway.app/

# Expected:
{
  "message": "Rank Simulator API",
  "version": "2.0",
  "endpoints": { ... }
}

# Test login
curl -X POST https://mvp-ranksimulator-production.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ciccioragusa@gmail.com","password":"12345Aa!"}'

# Expected:
{
  "message": "Login successful",
  "user": { ... },
  "access_token": "eyJ0eXAi..."
}
```

---

## Alternativa: Deploy Diretto (Se GitHub non funziona)

Se hai problemi a connettere GitHub, puoi continuare a usare `railway up`:

```bash
# Ogni volta che fai modifiche
git add -A
git commit -m "Your message"
git push  # Push to GitHub
railway up --detach  # Deploy to Railway
```

Ma è meglio connettere GitHub per deploy automatici!

---

## Struttura Finale

```
GitHub Repository (Instilla-AI/mvp-ranksimulator)
    ↓ (webhook on push)
Railway Service (mvp-ranksimulator)
    ↓ (auto deploy)
PostgreSQL Database
    ↓
API Live: https://mvp-ranksimulator-production.up.railway.app
```

---

## Troubleshooting

### Repository non trovato
- Verifica che l'account Railway (`service@instilla.it`) abbia accesso al repository GitHub
- Potrebbe essere necessario autorizzare Railway app su GitHub

### Deploy fallisce
- Controlla i log: `railway logs`
- Verifica che tutte le variabili d'ambiente siano configurate
- Verifica che PostgreSQL sia attivo

### API restituisce HTML invece di JSON
- Significa che sta deployando il vecchio codice
- Verifica che il repository GitHub sia quello corretto
- Forza un nuovo deploy dopo aver connesso il repo

---

## Prossimi Passi

1. ✅ Repository GitHub aggiornato
2. ✅ Railway CLI configurato
3. ⏳ Connetti repository via dashboard
4. ⏳ Verifica deploy automatico
5. ⏳ Testa API endpoints
6. ⏳ Setup frontend

---

*Guida creata: November 5, 2025 at 1:55 PM*
