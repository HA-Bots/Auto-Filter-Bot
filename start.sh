if [ -z $UPSTREAM_REPO ]
then
  echo "Cloning main Repository"
  git clone https://github.com/Hansaka-Anuhas/AutoFilterBot.git /AutoFilterBot
else
  echo "Cloning Custom Repo from $UPSTREAM_REPO "
  git clone $UPSTREAM_REPO /AutoFilterBot
fi
cd /AutoFilterBot
pip3 install -U -r requirements.txt
echo "Starting Bot..."
python3 bot.py
