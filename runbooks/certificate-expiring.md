<b>1. Diagnostico</b>
<code>echo | openssl s_client -servername dominio.com -connect dominio.com:443 2>/dev/null | openssl x509 -noout -dates</code>

<b>2. Verificar validade</b>
- Data de expiracao
- Dominio coberto (SAN)
- Cadeia de certificados completa

<b>3. Renovacao - Let's Encrypt</b>
<code>certbot renew --dry-run</code>
<code>certbot renew</code>
<code>systemctl reload nginx</code>

<b>4. Renovacao - Certificado comprado</b>
- Gerar novo CSR: <code>openssl req -new -key private.key -out domain.csr</code>
- Enviar CSR para CA
- Instalar novo certificado
- Reload do web server

<b>5. Verificacao pos-renovacao</b>
<code>curl -vI https://dominio.com 2>&1 | grep "expire"</code>
- Testar em SSL Labs: ssllabs.com/ssltest

<b>6. Prevencao</b>
- Configurar auto-renovacao com certbot
- Alerta 30 dias antes da expiracao
- Monitoramento externo (UptimeRobot, etc)
- Documentar todos os certificados e datas
