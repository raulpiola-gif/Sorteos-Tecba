#!/bin/bash
cd "$(dirname "$0")"

export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH=$JAVA_HOME/bin:$PATH

clear
echo "================================"
echo "   SORTEO DE PARTICIPANTES"
echo "================================"
echo ""
echo "Iniciando servidor..."
echo ""

mvn spring-boot:run -q 2>/dev/null &
SERVER_PID=$!

for i in $(seq 1 30); do
    if curl -s http://localhost:8080/ > /dev/null 2>&1; then
        echo "Servidor listo. Abriendo navegador..."
        open http://localhost:8080
        break
    fi
    sleep 1
done

wait $SERVER_PID
