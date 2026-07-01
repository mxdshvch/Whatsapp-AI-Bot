#!/bin/bash

# Скрипт для настройки PostgreSQL на Ubuntu сервере
# Запускать с правами root: sudo bash setup_postgresql.sh

echo "🐘 Настройка PostgreSQL для WhatsApp ChatBot..."

# Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Установка PostgreSQL
echo "🔧 Установка PostgreSQL..."
apt install -y postgresql postgresql-contrib

# Запуск и включение PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Создание пользователя и базы данных
echo "👤 Создание пользователя и базы данных..."
sudo -u postgres psql << EOF
CREATE USER chatbot WITH PASSWORD 'change_me';
CREATE DATABASE chatbot_db OWNER chatbot;
GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot;
\q
EOF

# Настройка PostgreSQL для внешних подключений
echo "🌐 Настройка внешних подключений..."
PG_VERSION=$(sudo -u postgres psql -t -c "SELECT version();" | grep -oP '\d+\.\d+' | head -1)

# Резервная копия конфигурации
cp /etc/postgresql/$PG_VERSION/main/postgresql.conf /etc/postgresql/$PG_VERSION/main/postgresql.conf.backup
cp /etc/postgresql/$PG_VERSION/main/pg_hba.conf /etc/postgresql/$PG_VERSION/main/pg_hba.conf.backup

# Настройка postgresql.conf
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/$PG_VERSION/main/postgresql.conf
sed -i "s/#port = 5432/port = 5432/" /etc/postgresql/$PG_VERSION/main/postgresql.conf

# Настройка pg_hba.conf для разрешения подключений
echo "host    chatbot_db    chatbot    0.0.0.0/0    md5" >> /etc/postgresql/$PG_VERSION/main/pg_hba.conf

# Перезапуск PostgreSQL
systemctl restart postgresql

# Установка Python зависимостей для PostgreSQL
echo "🐍 Установка Python зависимостей..."
apt install -y python3-pip python3-venv
pip3 install psycopg2-binary

# Создание директории для проекта
echo "📁 Создание директории проекта..."
mkdir -p /opt/chatbot
chown -R $SUDO_USER:$SUDO_USER /opt/chatbot

# Настройка firewall (если используется ufw)
echo "🔥 Настройка firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 5432/tcp
    ufw allow 8000/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
fi

# Создание systemd сервиса
echo "⚙️ Создание systemd сервиса..."
cat > /etc/systemd/system/chatbot.service << EOF
[Unit]
Description=WhatsApp ChatBot
After=network.target postgresql.service

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=/opt/chatbot
Environment=PATH=/opt/chatbot/venv/bin
ExecStart=/opt/chatbot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Создание скрипта для управления
cat > /opt/chatbot/manage.sh << 'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "🚀 Запуск ChatBot..."
        sudo systemctl start chatbot
        sudo systemctl status chatbot
        ;;
    stop)
        echo "⏹️ Остановка ChatBot..."
        sudo systemctl stop chatbot
        ;;
    restart)
        echo "🔄 Перезапуск ChatBot..."
        sudo systemctl restart chatbot
        sudo systemctl status chatbot
        ;;
    status)
        sudo systemctl status chatbot
        ;;
    logs)
        sudo journalctl -u chatbot -f
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF

chmod +x /opt/chatbot/manage.sh

echo "✅ PostgreSQL настроен успешно!"
echo ""
echo "📋 Информация о подключении:"
echo "   Host: localhost (или IP сервера)"
echo "   Port: 5432"
echo "   Database: chatbot_db"
echo "   User: chatbot"
echo "   Password: change_me (замените в production)"
echo ""
echo "🔧 Следующие шаги:"
echo "1. Скопируйте файлы проекта в /opt/chatbot"
echo "2. Создайте виртуальное окружение: python3 -m venv venv"
echo "3. Активируйте окружение: source venv/bin/activate"
echo "4. Установите зависимости: pip install -r requirements.txt"
echo "5. Настройте .env файл с правильными данными БД"
echo "6. Запустите: ./manage.sh start"
echo ""
echo "🌐 Админ панель будет доступна по адресу: http://your-server-ip:8000/admin"
