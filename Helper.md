### Python 11 installer code on codespace
```bash
sudo apt update
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
libnss3-dev libssl-dev libreadline-dev libffi-dev curl libsqlite3-dev wget

wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar -xvf Python-3.11.9.tgz
cd Python-3.11.9
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall  # Use altinstall to avoid overwriting system python
```

```bash
/usr/local/bin/python3.11 -m venv venv
source venv/bin/activate
```