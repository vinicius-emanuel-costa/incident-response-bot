<b>1. Diagnostico</b>
<code>top -bn1 | head -20</code>
<code>ps aux --sort=-%cpu | head -10</code>

<b>2. Identificar processo</b>
- Verifique qual processo esta consumindo CPU
- Se for aplicacao: verifique logs recentes
- Se for sistema: verifique cron jobs ou atualizacoes

<b>3. Acoes imediatas</b>
- Se load > num_cores * 2: considere restart do servico
- Verifique se houve deploy recente
- Monitore com <code>htop</code> ou <code>dstat</code>

<b>4. Mitigacao</b>
- Escale horizontalmente se possivel
- Aplique rate limiting se for trafego
- Rollback se causado por deploy

<b>5. Prevencao</b>
- Configure alertas de CPU > 80% por 5min
- Implemente auto-scaling
- Review de performance em PRs
