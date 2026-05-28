import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
EMAIL_FROM  = os.environ.get('EMAIL_FROM',  'contato@cordium.com.br')
EMAIL_ADMIN = os.environ.get('EMAIL_ADMIN', 'claudio@damaro.com.br')


def _enviar(para: str, assunto: str, corpo_html: str):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = assunto
    msg['From']    = EMAIL_FROM
    msg['To']      = para
    msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))

    if not SMTP_HOST:
        # Modo local: imprime no console em vez de enviar
        sep = '=' * 60
        print(f'\n{sep}\n[E-MAIL SIMULADO — configure SMTP_HOST para envio real]\n'
              f'Para:    {para}\nAssunto: {assunto}\n{sep}\n{corpo_html}\n{sep}\n')
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as srv:
        srv.starttls()
        srv.login(SMTP_USER, SMTP_PASS)
        srv.send_message(msg)


def email_confirmacao_pedido(nome: str, email: str, horas: int,
                              codigo_pedido: str, chave_pix: str, valor: float):
    corpo = f"""
<h2 style="color:#2c3e50">Cordium — Pedido recebido ✅</h2>
<p>Olá, <strong>{nome}</strong>!</p>
<p>Seu pedido foi registrado. Veja os dados abaixo:</p>
<table style="border-collapse:collapse;font-family:Arial,sans-serif">
  <tr><td style="padding:4px 12px;font-weight:bold">Código do pedido:</td>
      <td style="padding:4px 12px;font-family:monospace;font-size:18px">{codigo_pedido}</td></tr>
  <tr><td style="padding:4px 12px;font-weight:bold">Horas solicitadas:</td>
      <td style="padding:4px 12px">{horas}h</td></tr>
  <tr><td style="padding:4px 12px;font-weight:bold">Valor total:</td>
      <td style="padding:4px 12px">R$ {valor:.2f}</td></tr>
</table>

<h3 style="color:#2c3e50">Como pagar:</h3>
<p>Chave PIX: <strong>{chave_pix}</strong></p>
<p style="background:#fff3cd;padding:10px;border-left:4px solid #ffc107">
  ⚠️ <strong>Coloque como descrição do PIX o código do pedido: {codigo_pedido}</strong><br>
  Isso nos permite identificar seu pagamento com segurança.
</p>

<h3 style="color:#2c3e50">Próximos passos:</h3>
<ol>
  <li>Realize o PIX acima com a descrição <strong>{codigo_pedido}</strong></li>
  <li>Responda este e-mail anexando o comprovante</li>
  <li>Em até 24h você receberá seu token de acesso por e-mail</li>
</ol>

<p style="background:#f8d7da;padding:10px;border-left:4px solid #dc3545">
  ⚠️ <strong>Atenção:</strong> O token tem validade de <strong>7 dias</strong> a partir do recebimento.<br>
  Após esse prazo expira definitivamente, sem direito a devolução.
</p>
<hr>
<p style="font-size:12px;color:#888">Cordium.com.br — {EMAIL_ADMIN}</p>
"""
    _enviar(email, f'Cordium — Pedido #{codigo_pedido} recebido', corpo)


def email_novo_pedido_admin(nome: str, email: str, cpf_cnpj: str,
                             horas: int, codigo_pedido: str, valor: float):
    corpo = f"""
<h2>Novo pedido recebido 🔔</h2>
<table style="border-collapse:collapse;font-family:monospace">
  <tr><td style="padding:4px 10px;font-weight:bold">Código:</td>  <td>{codigo_pedido}</td></tr>
  <tr><td style="padding:4px 10px;font-weight:bold">Nome:</td>    <td>{nome}</td></tr>
  <tr><td style="padding:4px 10px;font-weight:bold">E-mail:</td>  <td>{email}</td></tr>
  <tr><td style="padding:4px 10px;font-weight:bold">CPF/CNPJ:</td><td>{cpf_cnpj}</td></tr>
  <tr><td style="padding:4px 10px;font-weight:bold">Horas:</td>   <td>{horas}h</td></tr>
  <tr><td style="padding:4px 10px;font-weight:bold">Valor:</td>   <td>R$ {valor:.2f}</td></tr>
</table>
<p>Para emitir o token após confirmar o pagamento, use:</p>
<pre style="background:#f0f0f0;padding:10px">
POST /api/token/gerar
Header: X-Admin-Secret: &lt;sua senha admin&gt;
Body:   {{"codigo_pedido": "{codigo_pedido}"}}
</pre>
"""
    _enviar(EMAIL_ADMIN, f'[CORDIUM] Novo pedido #{codigo_pedido}', corpo)


def email_token_emitido(nome: str, email: str, token_id: str,
                         horas: int, data_expiracao: str):
    corpo = f"""
<h2 style="color:#155724">Cordium — Seu token de acesso 🎉</h2>
<p>Olá, <strong>{nome}</strong>! Pagamento confirmado.</p>
<p>Seu token de acesso ao SIM9:</p>
<p style="font-size:22px;font-family:monospace;background:#f0f0f0;padding:14px;
           border-radius:6px;word-break:break-all">
  <strong>{token_id}</strong>
</p>
<table style="border-collapse:collapse;font-family:Arial,sans-serif">
  <tr><td style="padding:4px 12px;font-weight:bold">Horas contratadas:</td>
      <td style="padding:4px 12px">{horas}h</td></tr>
  <tr><td style="padding:4px 12px;font-weight:bold">Expira em:</td>
      <td style="padding:4px 12px"><strong>{data_expiracao}</strong></td></tr>
</table>
<p style="background:#f8d7da;padding:10px;border-left:4px solid #dc3545;margin-top:16px">
  ⚠️ <strong>Este token expira em 7 dias ({data_expiracao}).</strong><br>
  Após esse prazo é invalidado definitivamente, sem devolução do valor pago.
</p>
<p>Insira o token na tela do SIM9 para liberar o acesso.</p>
<hr>
<p style="font-size:12px;color:#888">Cordium.com.br</p>
"""
    _enviar(email, 'Cordium — Token de acesso SIM9', corpo)
