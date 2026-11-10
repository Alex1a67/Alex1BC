"""Self-signed TLS certificate generator in pure Python (Blender ships without `cryptography`).

Phone browsers only expose motion sensors on secure (HTTPS) pages, so the add-on serves its
controller over HTTPS with a certificate created once on this computer and kept private.
"""
import base64, datetime, hashlib, math, os, secrets

_SMALL = [p for p in range(3, 2000, 2) if all(p % d for d in range(3, int(p ** .5) + 1, 2))]

def _is_prime(n, rounds=24):
    if n < 4:
        return n in (2, 3)
    if n % 2 == 0:
        return False
    for p in _SMALL:
        if n == p:
            return True
        if n % p == 0:
            return False
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2; r += 1
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def _gen_prime(bits):
    while True:
        n = secrets.randbits(bits) | (1 << (bits - 1)) | (1 << (bits - 2)) | 1
        if _is_prime(n):
            return n

def generate_rsa(bits=2048, e=65537):
    while True:
        p, q = _gen_prime(bits // 2), _gen_prime(bits // 2)
        if p == q:
            continue
        lam = (p - 1) * (q - 1) // math.gcd(p - 1, q - 1)
        if math.gcd(e, lam) != 1:
            continue
        n = p * q
        if n.bit_length() != bits:
            continue
        return dict(n=n, e=e, d=pow(e, -1, lam), p=p, q=q)

# ---- minimal DER encoder
def _len(n):
    if n < 128:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, 'big')
    return bytes([0x80 | len(b)]) + b

def _tlv(tag, body):
    return bytes([tag]) + _len(len(body)) + body

def _int(n):
    b = n.to_bytes(max(1, (n.bit_length() + 8) // 8), 'big')
    return _tlv(0x02, b)

def _seq(*items): return _tlv(0x30, b''.join(items))
def _set(*items): return _tlv(0x31, b''.join(items))
def _oid(s):
    a = [int(x) for x in s.split('.')]
    out = bytes([a[0] * 40 + a[1]])
    for v in a[2:]:
        chunk = [v & 0x7f]
        v >>= 7
        while v:
            chunk.append(0x80 | (v & 0x7f)); v >>= 7
        out += bytes(reversed(chunk))
    return _tlv(0x06, out)
def _utf8(s): return _tlv(0x0c, s.encode())
def _time(dt): return _tlv(0x17, dt.strftime('%y%m%d%H%M%SZ').encode())
def _bits(b): return _tlv(0x03, b'\x00' + b)
def _octets(b): return _tlv(0x04, b)
NULL = b'\x05\x00'
SHA256_RSA = _seq(_oid('1.2.840.113549.1.1.11'), NULL)

def _pem(label, der):
    b = base64.b64encode(der).decode()
    return f"-----BEGIN {label}-----\n" + '\n'.join(b[i:i+64] for i in range(0, len(b), 64)) + f"\n-----END {label}-----\n"

def build_certificate(key, common_name="Alex1BC", days=825, dns=("alex1bc.local", "localhost"), ips=("127.0.0.1",)):
    n, e, d = key['n'], key['e'], key['d']
    pub = _seq(_int(n), _int(e))
    name = _seq(_set(_seq(_oid('2.5.4.3'), _utf8(common_name))))
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0) - datetime.timedelta(days=1)
    san = b''.join([_tlv(0x82, x.encode()) for x in dns] + [_tlv(0x87, bytes(int(o) for o in ip.split('.'))) for ip in ips])
    exts = _seq(
        _seq(_oid('2.5.29.19'), _tlv(0x01, b'\xff'), _octets(_seq())),                       # basicConstraints (critical)
        _seq(_oid('2.5.29.37'), _octets(_seq(_oid('1.3.6.1.5.5.7.3.1')))),                   # extKeyUsage: serverAuth
        _seq(_oid('2.5.29.17'), _octets(_seq(san))),                                         # subjectAltName
    )
    tbs = _seq(
        _tlv(0xa0, _int(2)), _int(secrets.randbits(63) + 1), SHA256_RSA, name,
        _seq(_time(now), _time(now + datetime.timedelta(days=days))), name,
        _seq(_seq(_oid('1.2.840.113549.1.1.1'), NULL), _bits(pub)),
        _tlv(0xa3, exts))
    k = (n.bit_length() + 7) // 8
    digest_info = _seq(_seq(_oid('2.16.840.1.101.3.4.2.1'), NULL), _octets(hashlib.sha256(tbs).digest()))
    em = b'\x00\x01' + b'\xff' * (k - len(digest_info) - 3) + b'\x00' + digest_info
    sig = pow(int.from_bytes(em, 'big'), d, n).to_bytes(k, 'big')
    cert_der = _seq(tbs, SHA256_RSA, _bits(sig))
    p, q = key['p'], key['q']
    priv = _seq(_int(0), _int(n), _int(e), _int(d), _int(p), _int(q), _int(d % (p - 1)), _int(d % (q - 1)), _int(pow(q, -1, p)))
    return _pem('CERTIFICATE', cert_der), _pem('RSA PRIVATE KEY', priv)

def ensure_cert(directory):
    """Return (cert_path, key_path); create them on first use."""
    os.makedirs(directory, exist_ok=True)
    cp, kp = os.path.join(directory, 'alex1bc-cert.pem'), os.path.join(directory, 'alex1bc-key.pem')
    if os.path.exists(cp) and os.path.exists(kp):
        return cp, kp
    cert, key = build_certificate(generate_rsa())
    with open(kp, 'w') as f:
        f.write(key)
    try:
        os.chmod(kp, 0o600)
    except OSError:
        pass
    with open(cp, 'w') as f:
        f.write(cert)
    return cp, kp


def fingerprint(cert_path):
    """SHA-256 of the DER certificate, upper-case hex (what the Android app pins)."""
    lines = [l for l in open(cert_path).read().splitlines() if l and not l.startswith('-----')]
    return hashlib.sha256(base64.b64decode(''.join(lines))).hexdigest().upper()
