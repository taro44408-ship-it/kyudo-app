# 弓道部 的中管理アプリ

## ファイル構成
```
kyudo-app/
├── app.py                    # メインページ（的中入力）
├── pages/
│   ├── 1_📊_的中率一覧.py    # 的中率の集計・グラフ
│   └── 2_👥_チーム編成.py    # チーム自動編成
├── .streamlit/
│   └── secrets.toml          # Supabase接続情報（※GitHubにはアップしない）
├── .gitignore
├── requirements.txt
└── README.md
```

## セットアップ手順

### 1. Supabase でデータベースを作る
1. https://supabase.com でアカウント作成
2. New Project → 名前: kyudo, Region: Tokyo
3. SQL Editor で以下を実行:
```sql
CREATE TABLE records (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  shots INTEGER NOT NULL,
  hits INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```
4. Project Settings → API から「Project URL」と「anon public Key」をメモ

### 2. secrets.toml を編集
`.streamlit/secrets.toml` を開き、メモした値を貼り付ける

### 3. 部員名を編集
`app.py` の MEMBERS リストを自分の部の部員名に書き換える

### 4. ローカルで動作確認
```bash
pip install -r requirements.txt
streamlit run app.py
```

### 5. GitHub にアップ
```bash
git init
git add .
git commit -m "初回コミット"
git branch -M main
git remote add origin https://github.com/ユーザー名/kyudo-app.git
git push -u origin main
```

### 6. Streamlit Community Cloud にデプロイ
1. https://share.streamlit.io にGitHubでログイン
2. New app → リポジトリ: kyudo-app, ブランチ: main, ファイル: app.py
3. Advanced settings → Secrets に secrets.toml の中身を貼り付け
4. Deploy
