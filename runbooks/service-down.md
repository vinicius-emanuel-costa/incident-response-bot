<b>1. Diagnostico</b>
<code>systemctl status nome-do-servico</code>
<code>curl -s -o /dev/null -w "%{http_code}" http://servico:porta/health</code>

<b>2. Verificar conectividade</b>
- DNS: <code>dig servico.interno</code>
- Rede: <code>ping -c 3 host</code>
- Porta: <code>nc -zv host porta</code>

<b>3. Verificar logs</b>
<code>journalctl -u nome-do-servico --since "10 minutes ago"</code>
<code>tail -100 /var/log/servico/error.log</code>

<b>4. Acoes imediatas</b>
- Restart do servico: <code>systemctl restart nome-do-servico</code>
- Se em container: <code>docker restart container</code>
- Verificar dependencias (DB, cache, filas)

<b>5. Se restart nao resolver</b>
- Verificar se ha OOM killer nos logs do kernel
- Checar recursos (memoria, disco, file descriptors)
- Verificar configuracao (rollback se deploy recente)

<b>6. Prevencao</b>
- Health checks configurados
- Auto-restart via systemd/k8s
- Redundancia (multiplas instancias)
