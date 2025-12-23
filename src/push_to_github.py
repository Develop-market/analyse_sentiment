import subprocess

def main():
    # 🔧 Liste prédéfinie des fichiers à ajouter
    file_list = [
        "resultats_sentiments.csv",
        "wordcloud.png",
        "absa_df.csv",
        "kpis.json",
        "requirement.txt",
         "postes.csv",
        "app.py"
    ]

    # ✅ Étape 1 : ajouter les fichiers sélectionnés
    print("\n📦 Fichiers à ajouter :")
    for file in file_list:
        print(f"  ➕ {file}")
    
    try:
        subprocess.run(["git", "add"] + file_list, check=True)
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de l'ajout des fichiers.")
        return

    # ✅ Étape 2 : demander un message de commit
    commit_message = input("\n✏️ Entrez le message de commit : ").strip()
    if not commit_message:
        commit_message = "Mise à jour automatique"

    try:
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
    except subprocess.CalledProcessError:
        print("❌ Aucune modification à commit ou erreur lors du commit.")
        return

    # ✅ Étape 3 : choisir la branche (optionnel)
    branch = "main"

    # ✅ Étape 4 : push vers GitHub
    try:
        subprocess.run(["git", "push", "origin", branch], check=True)
        print("✅ Fichiers poussés avec succès sur GitHub.")
    except subprocess.CalledProcessError:
        print("❌ Erreur lors du push. Vérifie ta connexion ou tes permissions.")

if __name__ == "__main__":
    main()
