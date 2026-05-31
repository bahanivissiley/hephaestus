from app.database.connection import SessionLocal, init_db
from app.database.models import Destination, Hotel, Attraction, Restaurant, HotelCategory, AttractionCategory, PriceRange

def seed():
    db = SessionLocal()
    
    # Vérifier si déjà seedé
    if db.query(Destination).count() > 0:
        print("✅ Base de données déjà peuplée")
        db.close()
        return

    print("🌱 Peuplement de la base de données...")

    # ─── TOKYO ────────────────────────────────────────────────────────────
    tokyo = Destination(
        name="Tokyo",
        country="Japon",
        continent="Asie",
        description="Tokyo, capitale du Japon, est une métropole fascinante qui mêle tradition millénaire et modernité futuriste. Avec ses quartiers aux identités distinctes, sa gastronomie exceptionnelle et ses cerisiers en fleur au printemps, Tokyo offre une expérience unique au monde.",
        best_periods=["mars", "avril", "octobre", "novembre"],
        budget_min=100,
        budget_max=200,
        currency="JPY",
        language="Japonais",
        climate="Tempéré avec 4 saisons. Printemps doux (15-20°C), été chaud et humide, automne coloré, hiver froid mais ensoleillé.",
        tips="Acheter un JR Pass avant le départ. Réserver les hébergements 2-3 mois à l'avance en avril (cerisiers). Utiliser le métro pour tous les déplacements. Apporter du cash — beaucoup de commerces n'acceptent pas les cartes.",
        image_url="https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800",
        latitude=35.6762,
        longitude=139.6503
    )
    db.add(tokyo)
    db.flush()

    db.add_all([
        Hotel(destination_id=tokyo.id, name="Shinjuku Granbell Hotel", category=HotelCategory.mid_range,
              price_min=80, price_max=120, currency="EUR", rating=8.4, location="Shinjuku",
              description="Hôtel moderne au cœur de Shinjuku, proche des transports et de la vie nocturne. Design contemporain et chambres confortables.",
              image_url="https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400",
              amenities=["wifi", "restaurant", "bar", "climatisation"], tags=["central", "moderne", "bien connecté"],
              latitude=35.6938, longitude=139.7034),
        Hotel(destination_id=tokyo.id, name="Khaosan Tokyo Origami", category=HotelCategory.budget,
              price_min=30, price_max=60, currency="EUR", rating=7.8, location="Asakusa",
              description="Auberge de jeunesse moderne dans le quartier historique d'Asakusa. Ambiance internationale et équipe accueillante.",
              image_url="https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=400",
              amenities=["wifi", "cuisine commune", "casiers"], tags=["budget", "social", "historique"],
              latitude=35.7148, longitude=139.7967),
        Hotel(destination_id=tokyo.id, name="Park Hyatt Tokyo", category=HotelCategory.luxe,
              price_min=350, price_max=600, currency="EUR", rating=9.2, location="Shinjuku",
              description="Hôtel de luxe iconique rendu célèbre par Lost in Translation. Vue panoramique sur Tokyo depuis les étages supérieurs.",
              image_url="https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400",
              amenities=["wifi", "spa", "piscine", "restaurant étoilé", "bar panoramique", "salle de sport"],
              tags=["luxe", "iconique", "vue panoramique", "gastronomie"],
              latitude=35.6897, longitude=139.6921),
        Hotel(destination_id=tokyo.id, name="Dormy Inn Asakusa", category=HotelCategory.mid_range,
              price_min=70, price_max=100, currency="EUR", rating=8.6, location="Asakusa",
              description="Hôtel japonais traditionnel avec onsen (bain thermal). Expérience authentique dans un quartier historique.",
              image_url="https://images.unsplash.com/photo-1590073242678-70ee3fc28f8a?w=400",
              amenities=["wifi", "onsen", "petit-déjeuner japonais"], tags=["onsen", "authentique", "traditionnel"],
              latitude=35.7103, longitude=139.7955),
    ])

    db.add_all([
        Attraction(destination_id=tokyo.id, name="Temple Senso-ji", category=AttractionCategory.monument,
                   description="Le plus ancien temple de Tokyo, fondé en 628. Incontournable avec sa grande porte Kaminarimon et ses échoppes de souvenirs. Magnifique au lever du soleil.",
                   image_url="https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=400",
                   price="Gratuit", duration_hours=2.0, best_time="Tôt le matin (7h-9h) pour éviter la foule",
                   location="Asakusa", tags=["incontournable", "gratuit", "histoire", "photos"],
                   rating=9.1, latitude=35.7148, longitude=139.7967),
        Attraction(destination_id=tokyo.id, name="Quartier de Shibuya", category=AttractionCategory.quartier,
                   description="Célèbre pour son carrefour piéton, le plus fréquenté au monde. Shopping, restaurants branchés, vie nocturne animée et vue depuis le Scramble Square.",
                   image_url="https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=400",
                   price="Gratuit", duration_hours=3.0, best_time="Soirée pour l'ambiance lumineuse",
                   location="Shibuya", tags=["shopping", "moderne", "incontournable", "photos", "nuit"],
                   rating=8.8, latitude=35.6580, longitude=139.7016),
        Attraction(destination_id=tokyo.id, name="Parc Shinjuku Gyoen", category=AttractionCategory.nature,
                   description="Magnifique parc national de 58 hectares avec jardins japonais, français et anglais. Le meilleur endroit de Tokyo pour les cerisiers en avril.",
                   image_url="https://images.unsplash.com/photo-1522383225653-ed111181a951?w=400",
                   price="500 JPY (~3€)", duration_hours=2.5, best_time="Avril pour les cerisiers, octobre pour les momiji",
                   location="Shinjuku", tags=["cerisiers", "nature", "détente", "photos", "saisonnier"],
                   rating=9.0, latitude=35.6851, longitude=139.7100),
        Attraction(destination_id=tokyo.id, name="Akihabara", category=AttractionCategory.quartier,
                   description="Le paradis de l'électronique, des mangas et de la culture otaku. Immersion totale dans la pop culture japonaise avec des dizaines d'étages de gadgets, figurines et jeux.",
                   image_url="https://images.unsplash.com/photo-1542051841857-5f90071e7989?w=400",
                   price="Gratuit (visites des magasins)", duration_hours=3.0, best_time="Après-midi et soirée",
                   location="Akihabara", tags=["manga", "technologie", "shopping", "geek", "unique"],
                   rating=8.5, latitude=35.7022, longitude=139.7742),
        Attraction(destination_id=tokyo.id, name="Mont Fuji (Hakone)", category=AttractionCategory.nature,
                   description="Excursion d'une journée depuis Tokyo pour voir le mont Fuji. Hakone offre des onsen, le lac Ashi et une vue spectaculaire sur le volcan sacré du Japon.",
                   image_url="https://images.unsplash.com/photo-1490806843957-31f4c9a91c65?w=400",
                   price="Transport JR Pass + 1000 JPY entrée", duration_hours=8.0,
                   best_time="Matin pour éviter les nuages, printemps et automne pour les meilleures vues",
                   location="Hakone (1h30 de Tokyo)", tags=["excursion", "nature", "icônique", "photos", "randonnée"],
                   rating=9.4, latitude=35.3606, longitude=138.7274),
    ])

    db.add_all([
        Restaurant(destination_id=tokyo.id, name="Ichiran Ramen", cuisine="Japonais - Ramen",
                   price_range=PriceRange.cheap, rating=8.9, location="Shinjuku",
                   description="Célèbre chaîne de ramen où on mange seul dans des cabines individuelles. Expérience unique et authentique. Le bouillon de porc est exceptionnel.",
                   image_url="https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?w=400",
                   tags=["incontournable", "local", "pas cher", "expérience", "ramen"]),
        Restaurant(destination_id=tokyo.id, name="Sushi Dai - Marché Toyosu", cuisine="Japonais - Sushi",
                   price_range=PriceRange.mid, rating=9.1, location="Toyosu",
                   description="Légendaire restaurant de sushi au marché de Toyosu. File d'attente de 2-3h mais expérience inoubliable. Les sushis les plus frais de Tokyo.",
                   image_url="https://images.unsplash.com/photo-1553621042-f6e147245754?w=400",
                   tags=["incontournable", "sushi", "authentique", "marché", "meilleur de tokyo"]),
        Restaurant(destination_id=tokyo.id, name="Gonpachi Nishi-Azabu", cuisine="Japonais - Izakaya",
                   price_range=PriceRange.mid, rating=8.3, location="Nishi-Azabu",
                   description="Restaurant izakaya rendu célèbre par Kill Bill. Architecture traditionnelle sur plusieurs niveaux. Yakitori, soba et saké dans un cadre spectaculaire.",
                   image_url="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400",
                   tags=["izakaya", "cinema", "ambiance", "yakitori", "iconique"]),
    ])

    # ─── PARIS ────────────────────────────────────────────────────────────
    paris = Destination(
        name="Paris",
        country="France",
        continent="Europe",
        description="Paris, la Ville Lumière, est l'une des destinations les plus visitées au monde. Art, gastronomie, mode et architecture se mêlent dans cette capitale romantique traversée par la Seine.",
        best_periods=["avril", "mai", "juin", "septembre", "octobre"],
        budget_min=80,
        budget_max=180,
        currency="EUR",
        language="Français",
        climate="Tempéré océanique. Printemps doux (15-20°C), été chaud, automne agréable, hiver froid et gris.",
        tips="Réserver les musées en ligne pour éviter les files. Utiliser le métro et le Vélib. Manger aux heures françaises (déjeuner 12h-14h, dîner 19h30-22h). Les prix sont plus abordables dans les arrondissements hors centre.",
        image_url="https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800",
        latitude=48.8566,
        longitude=2.3522
    )
    db.add(paris)
    db.flush()

    db.add_all([
        Hotel(destination_id=paris.id, name="Hôtel des Arts Montmartre", category=HotelCategory.mid_range,
              price_min=90, price_max=140, currency="EUR", rating=8.2, location="Montmartre",
              description="Charmant hôtel boutique à deux pas du Sacré-Cœur. Décoration artistique, personnel chaleureux et vue sur les toits parisiens.",
              image_url="https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400",
              amenities=["wifi", "petit-déjeuner", "terrasse"], tags=["charme", "artiste", "vue", "Montmartre"],
              latitude=48.8867, longitude=2.3431),
        Hotel(destination_id=paris.id, name="Generator Paris", category=HotelCategory.budget,
              price_min=35, price_max=80, currency="EUR", rating=7.9, location="10ème arrondissement",
              description="Auberge de jeunesse branchée dans le 10ème. Design moderne, bar animé et bonne connexion aux transports.",
              image_url="https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=400",
              amenities=["wifi", "bar", "restaurant", "terrasse"], tags=["jeune", "branché", "social", "central"],
              latitude=48.8761, longitude=2.3622),
        Hotel(destination_id=paris.id, name="Le Bristol Paris", category=HotelCategory.luxe,
              price_min=700, price_max=1500, currency="EUR", rating=9.5, location="8ème arrondissement",
              description="Palace parisien légendaire sur la rue du Faubourg Saint-Honoré. Service impeccable, restaurant trois étoiles Michelin et spa de rêve.",
              image_url="https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400",
              amenities=["wifi", "spa", "piscine", "restaurant 3 étoiles", "concierge 24h", "voiturier"],
              tags=["palace", "luxe absolu", "gastronomie", "service exceptionnel"],
              latitude=48.8728, longitude=2.3127),
    ])

    db.add_all([
        Attraction(destination_id=paris.id, name="Tour Eiffel", category=AttractionCategory.monument,
                   description="Le symbole de Paris et de la France. Construite en 1889 pour l'Exposition Universelle, la Tour Eiffel offre une vue imprenable sur Paris depuis ses trois étages.",
                   image_url="https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?w=400",
                   price="11-28€ selon étage", duration_hours=2.0, best_time="Au coucher du soleil ou la nuit pour les illuminations",
                   location="7ème arrondissement", tags=["incontournable", "symbole", "vue", "photos", "romantique"],
                   rating=9.3, latitude=48.8584, longitude=2.2945),
        Attraction(destination_id=paris.id, name="Musée du Louvre", category=AttractionCategory.musee,
                   description="Le plus grand musée du monde avec 35 000 œuvres exposées dont la Joconde et la Vénus de Milo. Prévoir au minimum une demi-journée.",
                   image_url="https://images.unsplash.com/photo-1499856871958-5b9357976b2f?w=400",
                   price="17€ (gratuit -26 ans UE)", duration_hours=4.0, best_time="Mercredi et vendredi soir (nocturnes jusqu'à 21h45)",
                   location="1er arrondissement", tags=["art", "incontournable", "histoire", "Joconde", "world class"],
                   rating=9.2, latitude=48.8606, longitude=2.3376),
        Attraction(destination_id=paris.id, name="Quartier de Montmartre", category=AttractionCategory.quartier,
                   description="Village dans la ville avec ses ruelles pavées, ses artistes, le Sacré-Cœur et une vue panoramique sur Paris. L'âme bohème et romantique de la capitale.",
                   image_url="https://images.unsplash.com/photo-1550340499-a6c60fc8287c?w=400",
                   price="Gratuit", duration_hours=3.0, best_time="Matin pour les ruelles vides, soirée pour l'ambiance",
                   location="18ème arrondissement", tags=["romantique", "artiste", "vue", "histoire", "bohème"],
                   rating=8.9, latitude=48.8867, longitude=2.3431),
        Attraction(destination_id=paris.id, name="Musée d'Orsay", category=AttractionCategory.musee,
                   description="Installé dans une ancienne gare, ce musée abrite la plus grande collection d'art impressionniste au monde avec Monet, Renoir, Van Gogh et Degas.",
                   image_url="https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?w=400",
                   price="16€ (gratuit -18 ans)", duration_hours=3.0, best_time="Jeudi soir (nocturne jusqu'à 21h45)",
                   location="7ème arrondissement", tags=["impressionnisme", "art", "architecture", "Van Gogh", "must-see"],
                   rating=9.1, latitude=48.8600, longitude=2.3266),
    ])

    db.add_all([
        Restaurant(destination_id=paris.id, name="Septime", cuisine="Français contemporain",
                   price_range=PriceRange.expensive, rating=9.3, location="11ème arrondissement",
                   description="L'un des meilleurs restaurants de Paris. Cuisine française créative avec des produits de saison. Réservation obligatoire 3 semaines à l'avance.",
                   image_url="https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400",
                   tags=["gastronomie", "bistronomie", "réservation", "saisonnier", "top paris"]),
        Restaurant(destination_id=paris.id, name="L'As du Fallafel", cuisine="Moyen-Orient - Falafel",
                   price_range=PriceRange.cheap, rating=8.7, location="Marais - 4ème arrondissement",
                   description="Institution du Marais depuis 1979. Les meilleurs falafels de Paris selon tous les guides. File d'attente permanente mais service rapide.",
                   image_url="https://images.unsplash.com/photo-1571197100525-db85c52d5b04?w=400",
                   tags=["incontournable", "pas cher", "Marais", "street food", "légendaire"]),
        Restaurant(destination_id=paris.id, name="Café de Flore", cuisine="Café français - Brasserie",
                   price_range=PriceRange.mid, rating=8.1, location="Saint-Germain-des-Prés",
                   description="Café historique de Saint-Germain-des-Prés, lieu de prédilection de Sartre, Beauvoir et Picasso. Croissants, café et terrasse parisienne par excellence.",
                   image_url="https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400",
                   tags=["historique", "café parisien", "terrasse", "littérature", "incontournable"]),
    ])

    # ─── MARRAKECH ────────────────────────────────────────────────────────
    marrakech = Destination(
        name="Marrakech",
        country="Maroc",
        continent="Afrique",
        description="Marrakech, la Ville Ocre, est un enchantement permanent. Ses souks labyrinthiques, ses riads cachés, ses palais et sa place Jemaa el-Fna classée au patrimoine de l'UNESCO en font une destination unique.",
        best_periods=["mars", "avril", "octobre", "novembre"],
        budget_min=40,
        budget_max=100,
        currency="MAD",
        language="Arabe, Français très parlé",
        climate="Semi-aride. Printemps chaud (20-28°C) et ensoleillé. Éviter l'été (40°C+). Hiver doux mais frais la nuit.",
        tips="Négocier les prix dans les souks (commencer à 30% du prix demandé). Porter des vêtements couvrants dans la médina. Surveiller ses affaires place Jemaa el-Fna. Prendre un guide local pour les souks les premières fois.",
        image_url="https://images.unsplash.com/photo-1489493887464-892be6d1daae?w=800",
        latitude=31.6295,
        longitude=-7.9811
    )
    db.add(marrakech)
    db.flush()

    db.add_all([
        Hotel(destination_id=marrakech.id, name="Riad Yasmine", category=HotelCategory.mid_range,
              price_min=60, price_max=100, currency="EUR", rating=9.0, location="Médina",
              description="Magnifique riad traditionnel avec piscine turquoise, patio fleuri et terrasse avec vue sur les toits de la médina. Petit-déjeuner marocain inclus.",
              image_url="https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=400",
              amenities=["wifi", "piscine", "petit-déjeuner", "terrasse", "hammam"],
              tags=["riad", "authentique", "piscine", "charme", "romantique"],
              latitude=31.6317, longitude=-7.9898),
        Hotel(destination_id=marrakech.id, name="Equity Point Marrakech", category=HotelCategory.budget,
              price_min=15, price_max=35, currency="EUR", rating=7.5, location="Médina",
              description="Auberge de jeunesse bien située dans la médina. Rooftop avec vue, ambiance internationale et prix imbattables.",
              image_url="https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400",
              amenities=["wifi", "rooftop", "cuisine commune"], tags=["budget", "social", "central", "routard"],
              latitude=31.6287, longitude=-7.9869),
        Hotel(destination_id=marrakech.id, name="La Mamounia", category=HotelCategory.luxe,
              price_min=500, price_max=1200, currency="EUR", rating=9.6, location="Médina",
              description="Le palace le plus légendaire du Maroc. Winston Churchill y séjournait régulièrement. Jardins d'exception, spa de luxe et service impeccable.",
              image_url="https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400",
              amenities=["wifi", "3 piscines", "spa", "5 restaurants", "jardin 8 hectares", "tennis"],
              tags=["palace", "légendaire", "jardin", "luxe absolu", "Churchill"],
              latitude=31.6231, longitude=-7.9925),
    ])

    db.add_all([
        Attraction(destination_id=marrakech.id, name="Place Jemaa el-Fna", category=AttractionCategory.quartier,
                   description="Le cœur vivant de Marrakech. Le jour : charmeurs de serpents, conteurs, henné. Le soir : dizaines de stands de nourriture, musiciens et acrobates. Classée au patrimoine UNESCO.",
                   image_url="https://images.unsplash.com/photo-1489493887464-892be6d1daae?w=400",
                   price="Gratuit", duration_hours=3.0, best_time="Coucher du soleil pour la transformation magique de la place",
                   location="Médina", tags=["incontournable", "gratuit", "culture", "gastronomie", "spectacle"],
                   rating=9.2, latitude=31.6259, longitude=-7.9891),
        Attraction(destination_id=marrakech.id, name="Jardins Majorelle", category=AttractionCategory.nature,
                   description="Jardin botanique exceptionnel créé par le peintre Jacques Majorelle, racheté par Yves Saint Laurent. Villa bleue cobalt entourée de bambous, cactus et bassins.",
                   image_url="https://images.unsplash.com/photo-1548013146-72479768bada?w=400",
                   price="150 MAD (~14€)", duration_hours=1.5, best_time="Tôt le matin (9h) avant la chaleur et la foule",
                   location="Guéliz", tags=["jardin", "art", "YSL", "photos", "botanique"],
                   rating=8.8, latitude=31.6418, longitude=-8.0035),
        Attraction(destination_id=marrakech.id, name="Les Souks de Marrakech", category=AttractionCategory.quartier,
                   description="Labyrinthe de ruelles spécialisées : souk des épices, des tapis, du cuir, des bijoux... Une expérience sensorielle totale. Négocier est la règle.",
                   image_url="https://images.unsplash.com/photo-1553899017-28e0de13f5fc?w=400",
                   price="Gratuit (achats selon budget)", duration_hours=3.0, best_time="Matin pour les commerçants encore de bonne humeur",
                   location="Médina", tags=["shopping", "artisanat", "culture", "expérience", "négociation"],
                   rating=8.6, latitude=31.6318, longitude=-7.9843),
        Attraction(destination_id=marrakech.id, name="Palais Bahia", category=AttractionCategory.monument,
                   description="Palais du 19ème siècle construit pour le grand vizir Ba Ahmed. Jardins parfumés, salles richement décorées de zellige, stuc et cèdre sculpté.",
                   image_url="https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=400",
                   price="70 MAD (~6€)", duration_hours=1.5, best_time="Matin pour la lumière",
                   location="Médina", tags=["palais", "architecture", "histoire", "jardins"],
                   rating=8.3, latitude=31.6213, longitude=-7.9832),
    ])

    db.add_all([
        Restaurant(destination_id=marrakech.id, name="Nomad", cuisine="Marocain contemporain",
                   price_range=PriceRange.mid, rating=8.9, location="Médina",
                   description="Restaurant rooftop avec vue sur les toits de la médina. Cuisine marocaine revisitée avec des produits locaux. L'adresse branchée de Marrakech.",
                   image_url="https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400",
                   tags=["rooftop", "vue", "moderne", "marocain", "branché"]),
        Restaurant(destination_id=marrakech.id, name="Chez Lamine Hadj Mustapha", cuisine="Marocain - Méchoui",
                   price_range=PriceRange.cheap, rating=8.7, location="Souk Semmarine",
                   description="Institution pour le méchoui (agneau rôti). Cave voûtée, tables collectives, méchoui découpé devant vous. Expérience authentique et délicieuse.",
                   image_url="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400",
                   tags=["méchoui", "authentique", "local", "incontournable", "pas cher"]),
    ])

    # ─── LISBONNE ─────────────────────────────────────────────────────────
    lisbonne = Destination(
        name="Lisbonne",
        country="Portugal",
        continent="Europe",
        description="Lisbonne, la capitale aux sept collines, séduit par son atmosphère mélancolique et chaleureuse. Tramways vintage, azulejos bleutés, fado nostalgique et pastéis de nata font le charme de cette ville authentique.",
        best_periods=["mars", "avril", "mai", "septembre", "octobre"],
        budget_min=60,
        budget_max=120,
        currency="EUR",
        language="Portugais",
        climate="Méditerranéen. Printemps doux et ensoleillé (18-24°C). Été chaud et sec. Hiver doux mais pluvieux.",
        tips="Utiliser le tram 28 pour traverser la ville (attention aux pickpockets). Acheter la Lisboa Card pour les transports et musées. Manger au déjeuner pour les menus du jour moins chers. Réserver les restaurants populaires à l'avance.",
        image_url="https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=800",
        latitude=38.7223,
        longitude=-9.1393
    )
    db.add(lisbonne)
    db.flush()

    db.add_all([
        Hotel(destination_id=lisbonne.id, name="LX Boutique Hotel", category=HotelCategory.mid_range,
              price_min=70, price_max=110, currency="EUR", rating=8.5, location="Chiado",
              description="Hôtel boutique au cœur du Chiado branché. Design portugais contemporain, rooftop avec vue sur le Tage et le château.",
              image_url="https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400",
              amenities=["wifi", "rooftop bar", "petit-déjeuner", "climatisation"],
              tags=["boutique", "central", "rooftop", "design"], latitude=38.7098, longitude=-9.1407),
        Hotel(destination_id=lisbonne.id, name="Home Lisbon Hostel", category=HotelCategory.budget,
              price_min=20, price_max=45, currency="EUR", rating=9.1, location="Baixa",
              description="L'un des meilleurs hostels d'Europe selon Hostelworld. Atmosphère familiale, personnel exceptionnel et localisation idéale.",
              image_url="https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=400",
              amenities=["wifi", "cuisine", "terrasse", "dîner communautaire"],
              tags=["meilleur hostel", "social", "familial", "central"], latitude=38.7131, longitude=-9.1368),
        Hotel(destination_id=lisbonne.id, name="Bairro Alto Hotel", category=HotelCategory.luxe,
              price_min=300, price_max=600, currency="EUR", rating=9.3, location="Bairro Alto",
              description="Palace contemporain dans le quartier le plus bohème de Lisbonne. Terrasse panoramique, spa de luxe et restaurant étoilé.",
              image_url="https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400",
              amenities=["wifi", "spa", "terrasse panoramique", "restaurant étoilé", "bar"],
              tags=["luxe", "vue", "bohème", "gastronomie"], latitude=38.7117, longitude=-9.1432),
    ])

    db.add_all([
        Attraction(destination_id=lisbonne.id, name="Quartier d'Alfama", category=AttractionCategory.quartier,
                   description="Le quartier le plus ancien de Lisbonne, avec ses ruelles escarpées, ses maisons colorées et ses miradouros. Le berceau du fado et de l'âme lisboète.",
                   image_url="https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=400",
                   price="Gratuit", duration_hours=3.0, best_time="Soirée pour entendre le fado dans les tavernes",
                   location="Alfama", tags=["incontournable", "fado", "histoire", "photos", "authentique"],
                   rating=9.0, latitude=38.7118, longitude=-9.1286),
        Attraction(destination_id=lisbonne.id, name="Monastère des Jéronimos", category=AttractionCategory.monument,
                   description="Chef-d'œuvre de l'architecture manuéline, construit au 16ème siècle. Vasco de Gama y est enterré. L'un des monuments les plus impressionnants du Portugal.",
                   image_url="https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400",
                   price="10€", duration_hours=1.5, best_time="Matin tôt pour éviter les groupes",
                   location="Belém", tags=["UNESCO", "architecture", "histoire", "Vasco de Gama", "incontournable"],
                   rating=9.1, latitude=38.6978, longitude=-9.2063),
        Attraction(destination_id=lisbonne.id, name="Sintra", category=AttractionCategory.nature,
                   description="Excursion d'une journée incontournable à 40min de Lisbonne. Palais de conte de fées accrochés aux collines, jardins féeriques et villas romantiques.",
                   image_url="https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=400",
                   price="Transport + entrées 15-20€", duration_hours=8.0,
                   best_time="Semaine pour éviter la foule du weekend",
                   location="Sintra (40min de Lisbonne)", tags=["excursion", "château", "nature", "UNESCO", "romantique"],
                   rating=9.3, latitude=38.7979, longitude=-9.3900),
    ])

    db.add_all([
        Restaurant(destination_id=lisbonne.id, name="Time Out Market", cuisine="Portugais - Varié",
                   price_range=PriceRange.mid, rating=8.8, location="Cais do Sodré",
                   description="Le meilleur marché gastronomique de Lisbonne. 40 restaurants sélectionnés parmi les meilleurs chefs portugais sous un même toit historique.",
                   image_url="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400",
                   tags=["incontournable", "varié", "gastronomie", "ambiance", "marché"]),
        Restaurant(destination_id=lisbonne.id, name="A Cevicheria", cuisine="Péruvien - Ceviche",
                   price_range=PriceRange.mid, rating=9.0, location="Príncipe Real",
                   description="Le meilleur ceviche de Lisbonne par le chef Kiko Martins. Fusion péruviano-portugaise inventive. Réservation indispensable.",
                   image_url="https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400",
                   tags=["ceviche", "fusion", "chef étoilé", "réservation", "top lisbonne"]),
        Restaurant(destination_id=lisbonne.id, name="Pastéis de Belém", cuisine="Café portugais - Pâtisserie",
                   price_range=PriceRange.cheap, rating=9.4, location="Belém",
                   description="La maison originale des pastéis de nata depuis 1837. La recette est secrète et unique. File d'attente permanente mais les meilleurs pastéis du monde.",
                   image_url="https://images.unsplash.com/photo-1571197100525-db85c52d5b04?w=400",
                   tags=["incontournable", "pastéis", "historique", "petit-déjeuner", "unique"]),
    ])

    db.commit()
    print("✅ Base de données peuplée avec succès !")
    print(f"   - {db.query(Destination).count()} destinations")
    print(f"   - {db.query(Hotel).count()} hôtels")
    print(f"   - {db.query(Attraction).count()} attractions")
    print(f"   - {db.query(Restaurant).count()} restaurants")
    db.close()

if __name__ == "__main__":
    init_db()
    seed()