#!/bin/bash

# Скрипт для развертывания WhatsApp ChatBot на Ubuntu сервере
# Запускать с правами root: sudo bash deploy.sh

echo "🚀 Развертывание WhatsApp ChatBot на Ubuntu сервере..."

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo bash deploy.sh"
    exit 1
fi

# Переменные
PROJECT_DIR="/opt/chatbot"
SERVICE_USER="chatbot"
SERVICE_NAME="chatbot"

# Создание пользователя для сервиса
echo "👤 Создание пользователя $SERVICE_USER..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d $PROJECT_DIR $SERVICE_USER
    echo "✅ Пользователь $SERVICE_USER создан"
else
    echo "ℹ️ Пользователь $SERVICE_USER уже существует"
fi

# Создание директории проекта
echo "📁 Создание директории проекта..."
mkdir -p $PROJECT_DIR
chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR

# Копирование файлов проекта
echo "📋 Копирование файлов проекта..."
cp -r . $PROJECT_DIR/
chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR

# Переход в директорию проекта
cd $PROJECT_DIR

# Создание виртуального окружения
echo "🐍 Создание виртуального окружения..."
sudo -u $SERVICE_USER python3 -m venv venv

# Активация окружения и установка зависимостей
echo "📦 Установка зависимостей..."
sudo -u $SERVICE_USER bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Создание .env файла если его нет
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚙️ Создание .env файла..."
    sudo -u $SERVICE_USER cat > $PROJECT_DIR/.env << 'EOF'
# Database
DATABASE_URL=postgresql://chatbot:change_me@localhost:5432/chatbot_db

# OpenRouter API
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=meta-llama/llama-2-70b-chat

# Wappi API
WAPPI_TOKEN=your_wappi_token_here
WAPPI_INSTANCE_ID=your_wappi_instance_id_here

# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me

# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=False
EOF
    echo "✅ .env файл создан. Не забудьте добавить ваши API ключи!"
fi

# Создание systemd сервиса
echo "⚙️ Создание systemd сервиса..."
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=WhatsApp ChatBot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Безопасность
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
systemctl daemon-reload

# Создание скрипта управления
echo "🔧 Создание скрипта управления..."
cat > $PROJECT_DIR/manage.sh << 'EOF'
#!/bin/bash

PROJECT_DIR="/opt/chatbot"
SERVICE_NAME="chatbot"

case "$1" in
    start)
        echo "🚀 Запуск ChatBot..."
        sudo systemctl start $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME
        ;;
    stop)
        echo "⏹️ Остановка ChatBot..."
        sudo systemctl stop $SERVICE_NAME
        ;;
    restart)
        echo "🔄 Перезапуск ChatBot..."
        sudo systemctl restart $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME
        ;;
    status)
        sudo systemctl status $SERVICE_NAME
        ;;
    logs)
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    update)
        echo "📦 Обновление зависимостей..."
        cd $PROJECT_DIR
        sudo -u chatbot bash -c "source venv/bin/activate && pip install --upgrade -r requirements.txt"
        sudo systemctl restart $SERVICE_NAME
        ;;
    backup)
        echo "💾 Создание резервной копии..."
        BACKUP_DIR="/opt/backups/chatbot"
        mkdir -p $BACKUP_DIR
        BACKUP_FILE="$BACKUP_DIR/chatbot_$(date +%Y%m%d_%H%M%S).sql"
        sudo -u postgres pg_dump chatbot_db > $BACKUP_FILE
        echo "✅ Резервная копия создана: $BACKUP_FILE"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|update|backup}"
        exit 1
        ;;
esac
EOF

chmod +x $PROJECT_DIR/manage.sh

# Настройка firewall
echo "🔥 Настройка firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 8000/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo "✅ Firewall настроен"
fi

# Создание cron задачи для резервного копирования
echo "⏰ Настройка автоматического резервного копирования..."
(crontab -u $SERVICE_USER -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/manage.sh backup") | crontab -u $SERVICE_USER -

# Инициализация базы данных
echo "🗄️ Инициализация базы данных..."
sudo -u $SERVICE_USER bash -c "cd $PROJECT_DIR && source venv/bin/activate && python init_knowledge_base.py"

# Включение автозапуска
systemctl enable $SERVICE_NAME

echo "✅ Развертывание завершено успешно!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте $PROJECT_DIR/.env и добавьте ваши API ключи"
echo "2. Запустите сервис: $PROJECT_DIR/manage.sh start"
echo "3. Проверьте статус: $PROJECT_DIR/manage.sh status"
echo "4. Просмотрите логи: $PROJECT_DIR/manage.sh logs"
echo ""
echo "🌐 Админ панель будет доступна по адресу: http://your-server-ip:8000/admin"
echo "👤 Логин и пароль — из вашего .env (ADMIN_USERNAME / ADMIN_PASSWORD)"
echo ""
echo "🔧 Управление сервисом:"
echo "   $PROJECT_DIR/manage.sh {start|stop|restart|status|logs|update|backup}"
