# MIX STUDIO v0.2 / PIN認証強化版

## GitHub → Cloudflare Pages
1. GitHubで Private リポジトリ `mix-studio` を作成し、このフォルダの中身をルートにアップロード。
2. Cloudflare ダッシュボードの Workers & Pages で Pages の Git リポジトリ連携を選び、対象を接続。フレームワークなし、ビルドコマンドなし、出力ディレクトリ `.` を設定。
3. Pages プロジェクトの設定で環境変数（Secret） `ACCESS_PASSWORD` と `SESSION_SECRET` を設定。後者は32文字以上の独立したランダム文字列。Production と Preview の両方を設定するか Preview を無効化。
4. Cloudflare D1 で `mix-studio-auth` データベースを作成し、Console で `setup/schema.sql` のSQLを実行。Pagesプロジェクトの Settings > Bindings で D1 database binding `AUTH_DB` を追加し、作成したDBを指定。Previewにも設定するか無効化。
5. `ACCESS_PASSWORD` に指定の半角数字4桁を登録。
6. 再デプロイし、発行された HTTPS URL を開く。未認証でアプリが見えないこと、誤ったパスワードで拒否されること、ログアウトできることを確認。

パスワードは GitHub に書かないこと。認証には署名付き Cookie を使用。パスワード変更で既存セッションも無効になります。全利用者共通で15分の固定時間枠につきログイン試行5回まで許可（成功も含む）。6回目以降は時間枠の終了まで拒否。第三者によるロックアウトや時間枠をまたぐ試行は防ぎきれません。4桁PINは弱いため、Cloudflare Accessのメール認証併用を推奨。D1未設定・障害時は認証を拒否します。GitHub Pages 単体ではこの認証は動きません。

## 操作
伴奏とボーカルを選択し、プリセットを選んで自動MIX。音量、EQ、低域カット、圧縮、リバーブ、位置を調整可能。MIX前は別途ボタンで作成。WAV 16bit/44.1kHz/ステレオ保存。音声は外部送信しません。対応形式はブラウザのデコード機能に依存します。固定時間制限はありませんが、長い音源はメモリを消費します。

## 未実装・検証状況
AIモデル、ピッチ・自動タイミング補正、ノイズ除去、録音、複数トラック、ハモリ、MP3出力、プロジェクト保存は未実装。現時点の自動MIXは信号処理ベースでありAIではありません。実音源での動作、音質、Cloudflare実環境での認証は未検証。
