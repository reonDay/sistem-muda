import os
import time
import random
import logging
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, TwoFactorRequired, ClientError

# ================================
# KONFIGURASI LOGGING
# ================================
LOG_FILENAME = "bot_stealth.log"

def setup_logger():
    logger = logging.getLogger("instagrapi_logger")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_FILENAME, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

# ================================
# DEFAULT KONFIGURASI
# ================================
DEFAULT_ACCOUNTS = """restisukawati,jasuke00
devanoaditama21,jasuke00
lia.santika24,jasuke00"""
DEFAULT_TARGET = "https://www.instagram.com/p/DPWSqohCp2a/"
DEFAULT_COMMENTS = "Keren!\nMantap!\nGood content!"

FALLBACK_RETRIES = 3
FALLBACK_BACKOFF = 2

# ================================
# FUNGSI UTAMA
# ================================

def parse_accounts_input(text):
    accounts = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",", 2)]
        if len(parts) >= 2:
            accounts.append({
                "username": parts[0],
                "password": parts[1],
                "twofa": parts[2] if len(parts) > 2 else None
            })
    return accounts

def login_client_for_account(username: str, password: str, twofa: str = None, proxy: str = None) -> Client:
    session_file = f"session_{username}.json"
    cl = Client()
    if proxy:
        try:
            cl.set_proxy(proxy)
            logger.info(f"[{username}] Proxy set: {proxy}")
        except Exception as e:
            logger.warning(f"[{username}] Gagal set proxy: {e}")

    if os.path.exists(session_file):
        try:
            cl.load_settings(session_file)
            try:
                cl.login(username, password)
            except Exception:
                logger.debug(f"[{username}] load_settings ok, login refresh gagal tapi lanjut.")
            logger.info(f"[{username}] Session loaded dari {session_file}.")
            return cl
        except Exception:
            try:
                os.remove(session_file)
            except Exception:
                pass

    try:
        if twofa:
            cl.login(username, password, verification_code=twofa)
        else:
            cl.login(username, password)
    except TwoFactorRequired:
        logger.error(f"[{username}] Diperlukan 2FA/OTP.")
        raise RuntimeError(f"[{username}] Diperlukan kode 2FA/OTP. Tambahkan kode pada input akun (username,password,2fa).")
    except ChallengeRequired:
        logger.error(f"[{username}] ChallengeRequired: Verifikasi manual diperlukan.")
        raise RuntimeError(f"[{username}] Verifikasi IG (challenge) diperlukan; verifikasi manual lewat Instagram.")
    except ClientError as e:
        logger.error(f"[{username}] ClientError saat login: {e}")
        raise RuntimeError(f"[{username}] Login gagal: {e}")
    except Exception as e:
        logger.error(f"[{username}] Error tak terduga saat login: {e}")
        raise RuntimeError(f"[{username}] Login gagal: {e}")

    try:
        cl.dump_settings(session_file)
        logger.info(f"[{username}] Login sukses, session disimpan.")
    except Exception as e:
        logger.warning(f"[{username}] Gagal menyimpan session: {e}")

    return cl

def _fallback_private_comment(cl: Client, media_pk: int, comment_text: str) -> bool:
    for attempt in range(1, FALLBACK_RETRIES + 1):
        try:
            endpoint = f"media/{media_pk}/comment/"
            data = {"comment_text": comment_text}
            logger.debug(f"Fallback attempt {attempt} -> {endpoint}")
            resp = cl.private_request(endpoint, data=data)
            if isinstance(resp, dict) and (resp.get("status") == "ok" or "comment_id" in resp or "comment" in resp):
                return True
            return True
        except Exception as e:
            logger.warning(f"Fallback private_request gagal (attempt {attempt}): {e}")
            if attempt == FALLBACK_RETRIES:
                return False
            sleep_time = FALLBACK_BACKOFF ** (attempt - 1)
            logger.info(f"Tunggu {sleep_time} detik sebelum retry fallback...")
            time.sleep(sleep_time)
    return False

def run_buzzer_for_account(cl: Client, username: str, target_url: str, comments: list, comment_counts: dict, max_comments: int, delays: dict):
    try:
        pk = cl.media_pk_from_url(target_url)
    except Exception as e:
        logger.error(f"[{username}] Gagal konversi URL ke media_pk: {e}")
        return

    try:
        cl.media_like(pk)
        logger.info(f"[{username}] Liked media PK {pk}")
        time.sleep(delays.get("after_like", 5))
    except Exception as e:
        logger.warning(f"[{username}] Gagal like: {e}")
        if isinstance(e, ChallengeRequired) or "Challenge" in str(e):
            raise RuntimeError(f"[{username}] Verifikasi IG diperlukan.")

    current = comment_counts.get(username, 0)
    if current >= max_comments:
        logger.info(f"[{username}] Skip komentar: limit tercapai ({current}/{max_comments})")
        return

    komentar = random.choice(comments) if comments else ""
    if not komentar:
        logger.info(f"[{username}] Tidak ada komentar tersedia.")
        return

    try:
        cl.media_comment(pk, komentar)
        comment_counts[username] = current + 1
        logger.info(f"[{username}] Berhasil komentar: '{komentar}' ({comment_counts[username]}/{max_comments})")
        time.sleep(delays.get("after_comment", 5))
        return
    except Exception as e:
        logger.warning(f"[{username}] media_comment gagal: {e}")
        if isinstance(e, ChallengeRequired) or "Challenge" in str(e):
            raise RuntimeError(f"[{username}] Verifikasi IG diperlukan.")
        if "Please wait" in str(e) or "action_blocked" in str(e).lower() or "429" in str(e):
            logger.error(f"[{username}] Terdeteksi rate-limit/action-blocked: {e}")
            return

    try:
        ok = _fallback_private_comment(cl, pk, komentar)
        if ok:
            comment_counts[username] = current + 1
            logger.info(f"[{username}] Berhasil komentar (fallback): '{komentar}' ({comment_counts[username]}/{max_comments})")
            time.sleep(delays.get("after_comment", 5))
        else:
            logger.warning(f"[{username}] Fallback komentar gagal setelah beberapa percobaan.")
    except Exception as e:
        logger.error(f"[{username}] Exception saat fallback komentar: {e}")
        if isinstance(e, ChallengeRequired) or "Challenge" in str(e):
            raise RuntimeError(f"[{username}] Verifikasi IG diperlukan.")

def run_bot(config):
    """
    Fungsi utama untuk menjalankan bot
    Returns: dict dengan hasil eksekusi
    """
    results = {
        "success": False,
        "message": "",
        "logs": [],
        "stats": {}
    }
    
    try:
        accounts = parse_accounts_input(config["accounts_input"])
        comments = [c.strip() for c in config["comments_input"].splitlines() if c.strip()]
        
        if not accounts:
            results["message"] = "❌ Tidak ada akun yang dimasukkan"
            return results
        
        if not comments:
            results["message"] = "❌ Tidak ada komentar yang ditentukan"
            return results
        
        if not config["target_post"].strip():
            results["message"] = "❌ Masukkan URL postingan target"
            return results

        # Login semua akun
        clients = {}
        successful_logins = 0
        
        for acc in accounts:
            username = acc["username"]
            try:
                client = login_client_for_account(
                    username, 
                    acc["password"], 
                    acc.get("twofa"), 
                    config.get("proxy") or None
                )
                clients[username] = client
                successful_logins += 1
                logger.info(f"✅ Login berhasil: {username}")
            except Exception as e:
                logger.error(f"❌ Login gagal: {username} - {e}")

        if successful_logins == 0:
            results["message"] = "❌ Tidak ada akun yang berhasil login"
            return results

        # Jalankan proses utama
        comment_counts = {acc["username"]: 0 for acc in accounts}
        delays = {
            "after_like": config.get("delay_after_like", 5),
            "after_comment": config.get("delay_after_comment", 5)
        }
        clients_active = dict(clients)

        total_comments_sent = 0
        
        for round_idx in range(config.get("iterations", 1)):
            for username, cl in list(clients_active.items()):
                try:
                    run_buzzer_for_account(
                        cl, 
                        username, 
                        config["target_post"], 
                        comments, 
                        comment_counts, 
                        config.get("max_comments", 1), 
                        delays
                    )
                    # Simpan session
                    try:
                        cl.dump_settings(f"session_{username}.json")
                    except Exception:
                        pass
                except RuntimeError as err:
                    logger.error(str(err))
                    clients_active.pop(username, None)
                except Exception as e:
                    logger.error(f"[{username}] Error: {e}")
                    continue

                # Delay antar akun
                time.sleep(config.get("delay_between_accounts", 5))

            # Delay antar putaran
            if round_idx < config.get("iterations", 1) - 1:
                time.sleep(config.get("delay_between_rounds", 10))

        # Hitung statistik
        total_comments = sum(comment_counts.values())
        
        results["success"] = True
        results["message"] = f"✅ Proses selesai! {total_comments} komentar dikirim"
        results["stats"] = {
            "total_comments": total_comments,
            "active_accounts": len(clients_active),
            "total_accounts": len(accounts),
            "account_details": comment_counts
        }
        
    except Exception as e:
        results["message"] = f"❌ Error: {str(e)}"
        logger.error(f"Error dalam run_bot: {e}")
    
    return results