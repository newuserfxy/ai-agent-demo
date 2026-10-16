@echo off
git checkout main
copy .env.cloud .env
copy .streamlit\secrets.cloud.toml .streamlit\secrets.toml
echo 已切换到云端版（DeepSeek）