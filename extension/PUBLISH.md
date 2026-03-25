# Publish CodeDecay to the VS Code Marketplace

Follow these steps to make the extension **downloadable in VS Code** (and from [marketplace.visualstudio.com](https://marketplace.visualstudio.com)).

---

## 1. Create a Microsoft / Azure account (if needed)

- Go to [https://azure.microsoft.com](https://azure.microsoft.com) or [https://login.live.com](https://login.live.com) and sign in with a Microsoft account.

---

## 2. Create a publisher

1. Open **[Visual Studio Code Marketplace – Manage publishers](https://marketplace.visualstudio.com/manage)**.
2. Sign in with your Microsoft account.
3. Click **Create Publisher**.
4. Choose a **Publisher ID** (e.g. `codedecay` or `yourname`). This will appear in the extension URL.
5. Fill in **Display name** and **Logo** (optional). Save.

---

## 3. Set the publisher in the extension

In **`extension/package.json`**, set your publisher ID:

```json
"publisher": "your-publisher-id"
```

Replace `your-publisher-id` with the ID you created (e.g. `codedecay`).

Optional: update **repository** and **homepage** URLs if your repo is on GitHub:

```json
"repository": { "type": "git", "url": "https://github.com/YOUR_USERNAME/codedecay.git" },
"homepage": "https://github.com/YOUR_USERNAME/codedecay#readme",
"bugs": { "url": "https://github.com/YOUR_USERNAME/codedecay/issues" }
```

---

## 4. Install the packaging tool

From the **`extension`** folder:

```bash
cd "/Users/saipranavikasturi/Documents/projects/BUG PREVENTION BOT/codedecay/extension"
npm install
```

The project already includes `@vscode/vsce` as a dev dependency. To use it via `npx`:

```bash
npx @vscode/vsce package
```

Or install globally and run `vsce` directly:

```bash
npm install -g @vscode/vsce
vsce package
```

---

## 5. Create a Personal Access Token (PAT)

1. Go to **[Azure DevOps – User settings – Personal access tokens](https://dev.azure.com/?_a=personal-access-tokens)** (or open your Azure DevOps profile → Personal access tokens).
2. **New Token**.
3. Name it (e.g. `VS Code Marketplace`).
4. Set **Expiration** (e.g. 1 year).
5. Under **Scopes**, choose **Custom defined** and enable **Marketplace (Publish)**.
6. Create and **copy the token** (you won’t see it again).

---

## 6. Publish the extension

From the **`extension`** folder:

```bash
npm run compile
npx @vscode/vsce publish
```

When prompted:

- **Publisher:** your publisher ID (e.g. `codedecay`).
- **Personal Access Token:** paste the PAT you created.

After it finishes, the extension will be on the marketplace. It may take a few minutes to appear in search.

---

## 7. Install as a downloadable extension

Users can install it in two ways:

**From VS Code**

1. Open the **Extensions** view (Ctrl+Shift+X / Cmd+Shift+X).
2. Search for **CodeDecay**.
3. Click **Install**.

**From the web**

- Open:  
  `https://marketplace.visualstudio.com/items?itemName=YOUR-PUBLISHER-ID.codedecay`  
  (replace `YOUR-PUBLISHER-ID` with your publisher ID).
- Click **Install**.

---

## Updating the extension

1. Bump **version** in `package.json` (e.g. `1.0.0` → `1.0.1`).
2. Add an entry to **CHANGELOG.md** for the new version.
3. Run again:

   ```bash
   npm run compile
   npx @vscode/vsce publish
   ```

Use the same PAT (or a new one with **Marketplace (Publish)** scope).

---

## Package only (no publish)

To build a **.vsix** file for local or manual install (no marketplace):

```bash
npm run compile
npx @vscode/vsce package
```

This creates **`codedecay-1.0.0.vsix`**. Users can install it via:

**Extensions** → **...** → **Install from VSIX...** → select the file.
