<b>1. Diagnostico</b>
<code>df -h</code>
<code>du -sh /* 2>/dev/null | sort -rh | head -10</code>

<b>2. Identificar causa</b>
- Logs crescendo: <code>find /var/log -size +100M</code>
- Arquivos temporarios: <code>find /tmp -mtime +7</code>
- Docker: <code>docker system df</code>

<b>3. Acoes imediatas</b>
- Limpar logs antigos: <code>journalctl --vacuum-size=500M</code>
- Remover arquivos temp: <code>find /tmp -mtime +7 -delete</code>
- Docker cleanup: <code>docker system prune -af</code>

<b>4. Mitigacao</b>
- Configurar logrotate se nao configurado
- Mover dados para volume maior
- Expandir disco se cloud

<b>5. Prevencao</b>
- Alerta de disco > 85%
- Logrotate configurado para todos os servicos
- Monitoramento de crescimento de disco
