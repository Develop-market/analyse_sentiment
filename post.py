import time
import json
import re
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from unidecode import unidecode
# Configuration
GROUP_URL = "https://www.facebook.com/groups/656390831772336"
MAX_SCROLL_ATTEMPTS = 5
SCROLL_WAIT_TIME = 2
COMMENT_LOAD_WAIT = 4

index  = 0
# Initialisation du navigateur Edge
path_edge = "./"
path_c = "./commentaires/"
options = EdgeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-notifications")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
driver_path = path_edge + "edgedriver_win64/msedgedriver.exe"  
driver = webdriver.Edge(service=EdgeService(executable_path=driver_path), options=options)

data = pd.read_csv(path_c + "postes.csv")

def load_cookies():
    """Charger et injecter les cookies Facebook"""
    try:
        driver.get("https://web.facebook.com")
        time.sleep(3)
        
        with open("facebook_cookies.json", "r", encoding="utf-8") as file:
            cookies = json.load(file)
        
        print(f"📁 {len(cookies)} cookies chargés depuis le fichier")
        
        for cookie in cookies:
            # Nettoyer les attributs non supportés
            for key in ["sameSite", "storeId", "id", "hostOnly", "session"]:
                cookie.pop(key, None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"⚠️ Erreur avec le cookie {cookie.get('name', 'inconnu')}: {e}")
        
        print("✅ Cookies injectés avec succès")
        return True
        
    except FileNotFoundError:
        print("❌ Fichier facebook_cookies.json non trouvé!")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du chargement des cookies: {e}")
        return False

def verify_login():
    """Vérifier si l'utilisateur est connecté"""
    try:
        # Chercher des éléments indiquant qu'on n'est pas connecté
        login_indicators = [
            "//input[@name='email']",
            "//input[@name='pass']",
            "//a[contains(text(), 'Se connecter')]",
            "//button[contains(text(), 'Se connecter')]"
        ]
        
        for indicator in login_indicators:
            if driver.find_elements(By.XPATH, indicator):
                return False
        
        return True
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification de connexion: {e}")
        return False

def wait_for_facebook_page_loaded(timeout=60):
    """Attendre que la page Facebook soit complètement chargée"""
    print("🔄 Attente du chargement de la page Facebook...")
    
    # 1. Attendre que le document soit prêt
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("✅ Document ready")
    except TimeoutException:
        print("⚠️ Timeout document ready")
    
    # 2. Attendre les éléments principaux Facebook
    main_selectors = [
        "[role='main']",
        "[data-pagelet]",
        "div[id^='mount_']",
        "div[data-ad-comet-preview='message']",
        "div[role='article']"
    ]
    
    element_found = False
    for selector in main_selectors:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            print(f"✅ Élément principal trouvé: {selector}")
            element_found = True
            break
        except TimeoutException:
            continue
    
    if not element_found:
        print("⚠️ Aucun élément principal trouvé, continuons...")
    
    # 3. Attendre que les spinners/loaders disparaissent
    loader_selectors = [
        "[aria-label='Chargement...']",
        ".loading",
        ".spinner",
        "[role='progressbar']"
    ]
    
    for selector in loader_selectors:
        try:
            WebDriverWait(driver, 5).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
            )
            print(f"✅ Loader disparu: {selector}")
        except TimeoutException:
            continue
    
    # 4. Attendre stabilité du contenu
    try:
        wait_for_content_stability(
            selector="div[data-ad-comet-preview='message'], div[role='article']",
            timeout=20,
            stable_time=3
        )
    except Exception as e:
        print(f"⚠️ Erreur stabilité: {e}")
    
    print("✅ Page Facebook chargée!")
    return True

def wait_for_content_stability(selector, timeout=30, stable_time=3):
    """Attendre que le contenu soit stable"""
    print(f"🔄 Attente de stabilité du contenu: {selector}")
    
    start_time = time.time()
    last_count = 0
    stable_start = None
    
    while time.time() - start_time < timeout:
        try:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, selector))
            
            if current_count == last_count:
                if stable_start is None:
                    stable_start = time.time()
                elif time.time() - stable_start >= stable_time:
                    print(f"✅ Contenu stable: {current_count} éléments")
                    return True
            else:
                stable_start = None
                last_count = current_count
                print(f"📊 Éléments détectés: {current_count}")
            
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Erreur vérification stabilité: {e}")
            time.sleep(1)
    
    print(f"⚠️ Timeout stabilité après {timeout}s")
    return False

def scroll_page_and_load_content():
    """Faire défiler la page pour charger plus de contenu"""
    print("🔄 Scroll de la page pour charger le contenu...")
    data = []
    for i in range(MAX_SCROLL_ATTEMPTS):
        print(f"📜 Scroll {i+1}/{MAX_SCROLL_ATTEMPTS}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_WAIT_TIME)
        com = click_comment_buttons()
        data.extend(com)
    
    print("✅ Scroll terminé")

    # Récupération des commentaires de tous les posts visibles
    # data = click_comment_buttons()
    return data



from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException



def click_comment_buttons():
    """Analyse les textes des posts, détecte les mots-clés, puis récupère les commentaires"""
    print("🔄 Analyse des posts et clic sur les boutons de commentaires...")

    comments_data = []
    posts = driver.find_elements(By.CSS_SELECTOR, "div[role='article']")
    print(f"🔍 {len(posts)} posts trouvés")

    for i in range(len(posts)):
        try:
            print(f"🧩 Traitement du post {i + 1}/{len(posts)}")

            # ⚠️ Recharger la liste des posts à chaque boucle
            posts = driver.find_elements(By.CSS_SELECTOR, "div[role='article']")
            if i >= len(posts):
                break
            post = posts[i]

            # 🔹 Cliquer sur "Voir plus" s’il est visible
            try:
                voir_plus = post.find_element(
                    By.XPATH,
                    ".//div[@role='button' and (contains(text(), 'Voir plus') or contains(text(), 'En voir plus'))]"
                )
                if voir_plus.is_displayed():
                    driver.execute_script("arguments[0].click();", voir_plus)
                    time.sleep(1)
                    print("📌 Bouton 'Voir plus' cliqué")
            except NoSuchElementException:
                pass
            except StaleElementReferenceException:
                print("⚠️ Bouton 'Voir plus' obsolète, on passe au suivant")
                continue

            # 🔹 Récupération du texte du post
            try:
                # Récupère tous les blocs story_message (courte + longue)
                text_blocks = [
                    e.text.strip()
                    for e in post.find_elements(By.CSS_SELECTOR, "div[data-ad-rendering-role='story_message']")
                    if e.text.strip()
                ]

                if not text_blocks:
                    print("⚠️ Aucun texte trouvé pour ce post")
                    continue

                # Garde la version la plus longue (le texte complet)
                texte_post = max(text_blocks, key=len)
                print("📝 Texte du post récupéré.")
            except Exception as e:
                print(f"⚠️ Erreur lors de la récupération du texte : {e}")
                continue

            # 🔹 Extraire la date et l’auteur
            try:
                date_element = post.find_element(
                    By.XPATH,
                    ".//a[contains(@href, '/posts/') and contains(@href, '?__cft__[0]=')]"
                )
                date_str = date_element.text.strip()
                formatte_date = convertir_date_facebook(date_str)

                nom_elem = post.find_element(By.CSS_SELECTOR, "div.xu06os2.x1ok221b")
                nom = nom_elem.text.strip().split("·")[0].strip()
                print(f"📆 {formatte_date} - 👤 {nom}")
            except (NoSuchElementException, StaleElementReferenceException):
                formatte_date = None
                nom = "Auteur inconnu"

            # 🔹 Nettoyage du texte du post
            post_text = unidecode(texte_post).lower()
            post_text = re.sub(r'[^\w\s]', '', post_text)
            post_text = re.sub(r'\s+', ' ', post_text)

            # 🔹 Vérification du mot-clé
            if not post_contient_mot_cle(post_text):
                print("⛔ Aucun mot-clé détecté, post ignoré.")
                continue

            print("✅ Mot-clé trouvé, récupération des commentaires...")

            # 🔹 Cliquer sur le bouton de commentaires
            try:
                comment_button = post.find_element(By.CSS_SELECTOR, "div[id^='_r_'][role='button']")
                driver.execute_script("arguments[0].click();", comment_button)
                time.sleep(2)
            except (NoSuchElementException, StaleElementReferenceException):
                print("⚠️ Bouton de commentaire introuvable ou obsolète")
                continue

            # 🔹 Trouver le conteneur des commentaires
            container = find_comment_container()
            if not container:
                print("❌ Aucun container de commentaires trouvé")
                continue

            # 🔹 Extraire les commentaires
            commentaires = extract_comments(container)
            for c in commentaires:
                c["poste"] = post_text
                c["date_post"] = formatte_date
                c["auteur"] = nom

            comments_data.extend(commentaires)

            # 🔹 Fermer le container de commentaires
            for c in driver.find_elements(By.CSS_SELECTOR, "div[aria-label='Fermer']"):
                try:
                    if c.is_displayed():
                        driver.execute_script("arguments[0].click();", c)
                        time.sleep(1)
                        print("✅ Container fermé")
                        break
                except:
                    continue

        except StaleElementReferenceException:
            print(f"⚠️ Post {i} ignoré (élément obsolète)")
            continue
        except Exception as e:
            print(f"⚠️ Erreur sur le post {i}: {e}")
            continue

    return comments_data


def find_comment_container():
    """Trouver le container de commentaires avec différents sélecteurs"""
    print("🔍 Recherche du container de commentaires...")
    
    container_selectors = [
        "div.html-div.x14z9mp.xat24cr.x1lziwak.xexx8yu.xyri2b.x18d9i69.x1c1uobl.x1gslohp",
    ]
    
    for selector in container_selectors:
        try:
            container = driver.find_element(By.CSS_SELECTOR, selector)
            print(f"✅ Container trouvé avec: {selector}")
            return container
        except NoSuchElementException:
            print(f"⏳ Sélecteur non trouvé: {selector}")
            continue
    
    print("❌ Aucun container de commentaires trouvé")
    return None

def scroll_comment_container(container):
    """Faire défiler le container de commentaires jusqu'à stabilité"""
    print("🔄 Scroll du container de commentaires...")
    
    previous_children_count = 0

    
    while True:
        # Compter les enfants actuels
        current_children_count = len(container.find_elements(By.XPATH, "./*"))
        
        # Si le nombre d'enfants n'a pas changé, on sort
        if current_children_count == previous_children_count:
            print(f"✅ Scroll terminé. Nombre final d'enfants: {current_children_count}")
            break
        
        previous_children_count = current_children_count
        print(f"📊 Enfants trouvés: {current_children_count}")
        
        # Scroll vers le bas du container
        driver.execute_script("""
            var container = arguments[0];
            if (container.lastElementChild) {
                container.lastElementChild.scrollIntoView({ 
                    behavior: 'instant', 
                    block: 'end' 
                });
            }
        """, container)
        
        # Attendre que les nouveaux commentaires se chargent
        time.sleep(COMMENT_LOAD_WAIT)

def post_contient_mot_cle(post_text):
    """Vérifie si le texte contient un mot-clé sensible"""
    mots_cles = ["sgci", "société générale", "la générale","sgbci","societe generale","la generale","#SGCI","#sgci","la general","#sociétéGénérale"]
    post_text_lower = post_text
    return any(mot in post_text_lower for mot in mots_cles)



from datetime import datetime, timedelta
from selenium.webdriver.common.by import By

# Fonction pour convertir les dates relatives Facebook
import re
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By

import re
from datetime import datetime, timedelta

import re
from datetime import datetime, timedelta
# from unidecode import unidecode

def convertir_date_facebook(date_str):
    """Convertit une date Facebook en format JJ-MM-AAAA"""
    aujourd_hui = datetime.today()
    date_str = date_str.lower().strip()

    # Mapping mois français -> numéro
    mois = {
        "janvier":1, "février":2, "fevrier":2, "mars":3, "avril":4, "mai":5, "juin":6,
        "juillet":7, "août":8, "aout":8, "septembre":9, "octobre":10, "novembre":11, "décembre":12, "decembre":12
    }

    try:
        if "min" in date_str:
            minutes = int(re.search(r"(\d+)", date_str).group(1))
            date_finale = aujourd_hui - timedelta(minutes=minutes)

        elif "h" in date_str :
            heures = int(re.search(r"(\d+)", date_str).group(1))
            date_finale = aujourd_hui - timedelta(hours=heures)

        elif "j" in date_str:
            jours = int(re.search(r"(\d+)", date_str).group(1))
            date_finale = aujourd_hui - timedelta(days=jours)

        elif "sem" in date_str:
            semaines = int(re.search(r"(\d+)", date_str).group(1))
            date_finale = aujourd_hui - timedelta(weeks=semaines)

        elif "ans" in date_str or "an" in date_str:
            annees = int(re.search(r"(\d+)", date_str).group(1))
            date_finale = aujourd_hui - timedelta(days=annees * 365)

        elif re.match(r"\d{1,2} \w+", date_str):
            # Nettoyer "à HH:MM" si présent
            date_str = re.sub(r"\s*à\s*\d{1,2}:\d{2}", "", date_str).strip()
            # Séparer jour et mois
            parts = date_str.split()
            if len(parts) >= 2:
                jour = int(parts[0])
                mois_str = unidecode(parts[1])  # supprime les accents
                mois_num = mois.get(mois_str.lower(), None)
                if not mois_num:
                    return "Erreur de conversion"
                date_finale = datetime(aujourd_hui.year, mois_num, jour)
            else:
                return "Erreur de conversion"

        else:
            return "Format inconnu"

        return date_finale.strftime("%d-%m-%Y")

    except Exception:
        return "Erreur de conversion"


def extract_comments(container):
    """Extraction des commentaires Facebook avec auteur, texte, date"""
    print("🚀 Début de l'extraction des commentaires...")
    data = []

    try:
        scroll_comment_container(container)

        # 👉 Sélecteur de blocs complets de commentaire (parent de auteur + texte)
        full_comment_blocks = container.find_elements(By.XPATH, ".//div[contains(@class,'xv55zj0')]")
        print(f"✅ {len(full_comment_blocks)} blocs de commentaires trouvés.")

        for i, block in enumerate(full_comment_blocks):
            try:
                # 🔎 Nom de l’auteur
                try:
                    author_element = block.find_element(By.XPATH, ".//a[.//span[@dir='auto']]")
                    author_name = author_element.text.strip()
                except:
                    author_name = "Auteur inconnu"

                # 🔎 Texte du commentaire
                try:
                    comment_element = block.find_element(By.XPATH, ".//div[@dir='auto']")
                    comment_text = comment_element.text.strip()
                except:
                    comment_text = ""

                if not comment_text or len(comment_text) <= 1:
                    continue

                # 🔎 Date
                try:
                    parent = block.find_element(By.XPATH, ".//ancestor::div[@role='article']")
                    date_element = parent.find_element(
                        By.XPATH,
                        ".//a[contains(@href, 'comment_id=') and (contains(@href, '/posts/') or contains(@href, '/videos/'))]"
                    )
                    raw_date = date_element.text.strip()
                    formatted_date = convertir_date_facebook(raw_date)
                except:
                    formatted_date = "Date non trouvée"

                # ✅ Enregistrement
                data.append({
                    "date": formatted_date,
                    "auteur_com": author_name,
                    "source": "OLBCI",
                    "commentaire": comment_text
                })

            except Exception as e:
                print(f"⚠️ Erreur lors du traitement du bloc {i}: {e}")

        print(f"✅ Total des commentaires extraits: {len(data)}")

    except Exception as e:
        print(f"❌ Erreur générale lors de l'extraction: {e}")

    return data


def main():
    """Fonction principale"""
    print("🚀 Démarrage du scraper Facebook...")
    
    try:
        # 1. Charger les cookies
        if not load_cookies():
            print("❌ Impossible de charger les cookies")
            return
        
        # 2. Accéder à la page du groupe
        print(f"🔗 Accès au groupe: {GROUP_URL}")
        driver.get(GROUP_URL)
        
        # 3. Vérifier la connexion
        if not verify_login():
            print("❌ Vous n'êtes pas connecté!")
            return
        
        print("✅ Connexion vérifiée")
        
        # 4. Attendre le chargement complet
        wait_for_facebook_page_loaded()
        
        # 5. Scroll pour charger plus de contenu
        time.sleep(5)  # Petite pause pour éviter les problèmes de chargement
        comments_data = scroll_page_and_load_content()
        
        # 6. Extraire les commentaires
      
        
        if not comments_data:
            print("❌ Aucun commentaire extrait")
            return
        
        # 7. Sauvegarder les données
        df = pd.DataFrame(comments_data)
        df =  df.drop_duplicates()
        df_concat = pd.concat([data, df], ignore_index=True).drop_duplicates()
        filename = "postes.csv"
        df_concat.to_csv(filename, index=False)
        
        print(f"✅ Extraction terminée!")
        print(f"📁 Fichier sauvegardé: {filename}")
        print(f"📊 Nombre de commentaires: {len(df_concat)}")
        
        # Afficher un aperçu

        print("\n📝 Aperçu des premiers commentaires:")
        for i, comment in enumerate(comments_data[:3]):
            print(f"{i+1}. {comment['commentaire'][:100]}...")
        
    except KeyboardInterrupt:
        print("\n⚠️ Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
    finally:
        print("🔚 Fermeture du navigateur...")
        driver.quit()

if __name__ == "__main__":
    main()
