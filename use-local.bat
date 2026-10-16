@echo off
git checkout local
copy .env.local .env
copy .streamlit\secrets.local.toml .streamlit\secrets.toml
echo 已切换到本地版（Ollama）