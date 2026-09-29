#!/bin/bash
clear
echo "Deteniendo servidor..."
kill $(lsof -ti:8080) 2>/dev/null
if [ $? -eq 0 ]; then
    echo "Servidor detenido."
else
    echo "No hay servidor ejecutandose."
fi
echo ""
echo "Presiona cualquier tecla para cerrar..."
read -n 1
