# TODO — Déploiement Vercel

## [ ] 1. Installer ngrok
```bash
brew install ngrok
```
Créer un compte gratuit sur [ngrok.com](https://ngrok.com) pour obtenir un authtoken.

## [ ] 2. Configurer l'authtoken ngrok
```bash
ngrok config add-authtoken TON_TOKEN
```

## [ ] 3. Démarrer le backend et exposer via ngrok
Dans un terminal :
```bash
source .venv/bin/activate && uvicorn src.api.main:app --reload
```
Dans un autre terminal :
```bash
ngrok http 8000
```
Copier l'URL publique affichée (ex: `https://abc123.ngrok-free.app`).

## [ ] 4. Déployer le frontend sur Vercel
```bash
npx vercel
```
Vercel détecte automatiquement le `vercel.json` à la racine. Suivre les prompts.

## [ ] 5. Configurer `NEXT_PUBLIC_API_BASE_URL` dans Vercel
Dashboard Vercel → ton projet → **Settings → Environment Variables**

| Variable | Valeur |
|----------|--------|
| `NEXT_PUBLIC_API_BASE_URL` | `https://abc123.ngrok-free.app` |

> ⚠️ L'URL ngrok change à chaque redémarrage sur le plan gratuit.
> Ngrok offre 1 domaine statique gratuit — recommandé pour éviter de répéter cette étape.

## [ ] 6. Redéployer après avoir ajouté l'env var
`NEXT_PUBLIC_API_BASE_URL` est injectée au **build**, pas au runtime.
```bash
npx vercel --prod
```
Ou cliquer **Redeploy** dans le dashboard Vercel.
