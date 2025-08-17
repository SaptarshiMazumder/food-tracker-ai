# Quickstart

```bash
# 0) venv (recommended)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 1) Install deps
pip install -r requirements.txt

# 2) (optional) set Google CSE envs for source finding
cp .env.example .env  # edit with your keys

# 3) Build/append a unified index from two datasets (dev cap 150k per)
python indexer.py --datasets mmfood,gurumurthy --max_rows_per 150000 --append

# 4) Query by ingredients and fetch web sources (no dataset directions used)
python query.py -i "chicken, rice, onion, garlic" --top 5
```
