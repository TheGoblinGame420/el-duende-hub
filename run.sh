#!/bin/bash
# Arranca el Casino en segundo plano (el símbolo & es clave)
python cerebro/luxor_blackjack.py &

# Arranca también el bot de Trading (si quieres que funcione también)
python cerebro/luxor_pro.py &

# Arranca la WebApp en primer plano (para que Render no se apague)
gunicorn webapp.app:app
