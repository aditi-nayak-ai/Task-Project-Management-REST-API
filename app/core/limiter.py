from slowapi import Limiter
from slowapi.util import get_remote_address

# README's "Known Limitations" listed this: "No brute-force protection
# on auth endpoints." Per-IP limiting on /auth/* is the minimum viable
# fix; it does not stop a distributed credential-stuffing attack from
# many IPs, which needs account-level lockout or a WAF layer instead.
limiter = Limiter(key_func=get_remote_address)
