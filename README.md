SPYBANKMARKET

Ce projet vise à collecter des données via les réseaux sociaux (Facebook, Linkedin,etc.) afin d'analyser le ressenti des clients sur la banque. 


La méthode d'extraction est un scraping utilisant Selenium et BeautifulSoup. 

1- Extraction de données via les pages officielles des banques concernées
cmd : python Posts.py

2- Traitement des commentaires collectées
cmd : python traitement.py

3- Extraction des données des groupes (Observatoire Libre des Banques)
cmd : python post.py

4- Push des fichiers sur le repo github

cmd : python push_to_github.py


Les dependances sont dans le fichiers requirements.txt

NB: pour pouvoir acceder a facebook, il faudrait qu'une session soit active dans microsoftEdge, avoir obligatoirmeent dans les extensions du navigateur l'extension (EditThisCookie (V3)),c'est à partir dee cette extension qu'on collecte les données pour les mettre dans le fichier facebook_cookies.json
NB: Il faut aussi télécharger le edgedriver de la même version que le navigateur sur lequel on travaille et selon le PC.
Telecharger fr_core_news_md de spacy
analyse_sentiment_dash/
├── asset/
│   ├── logo.png
    |---style.css
│---Posts.py
|---post.py
|---traitement.py
|---push_to_github.py
├── requirements.txt
└── README.md