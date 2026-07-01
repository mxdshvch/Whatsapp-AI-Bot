#!/bin/bash

# Скрипт для настройки SSL сертификатов с Let's Encrypt
# Запускать с правами root: sudo bash setup_ssl.sh

echo "🔒 Настройка SSL сертификатов с Let's Encrypt..."

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo bash setup_ssl.sh"
    exit 1
fi

# Запрос домена
read -p "🌐 Введите ваш домен (например: example.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "❌ Домен не указан"
    exit 1
fi

# Установка Certbot
echo "📦 Установка Certbot..."
apt update
apt install -y certbot python3-certbot-nginx

# Остановка Nginx для получения сертификата
echo "⏹️ Остановка Nginx..."
systemctl stop nginx

# Получение SSL сертификата
echo "🔐 Получение SSL сертификата для $DOMAIN..."
certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# Проверка успешности получения сертификата
if [ $? -eq 0 ]; then
    echo "✅ SSL сертификат успешно получен"
else
    echo "❌ Ошибка получения SSL сертификата"
    exit 1
fi

# Обновление Nginx конфигурации
echo "⚙️ Обновление Nginx конфигурации..."
sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/chatbot

# Включение сайта
echo "🔗 Включение сайта..."
ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверка конфигурации Nginx
echo "🔍 Проверка конфигурации Nginx..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Конфигурация Nginx корректна"
    
    # Запуск Nginx
    echo "🚀 Запуск Nginx..."
    systemctl start nginx
    systemctl enable nginx
    
    # Настройка автоматического обновления сертификатов
    echo "⏰ Настройка автоматического обновления сертификатов..."
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    echo "✅ SSL настроен успешно!"
    echo ""
    echo "🌐 Ваш сайт доступен по адресу: https://$DOMAIN"
    echo "👤 Админ панель: https://$DOMAIN/admin"
    echo ""
    echo "📋 Не забудьте:"
    echo "1. Настроить DNS записи для $DOMAIN"
    echo "2. Добавить API ключи в .env файл"
    echo "3. Запустить ChatBot: /opt/chatbot/manage.sh start"
    
else
    echo "❌ Ошибка в конфигурации Nginx"
    echo "Проверьте файл: /etc/nginx/sites-available/chatbot"
    exit 1
fi
