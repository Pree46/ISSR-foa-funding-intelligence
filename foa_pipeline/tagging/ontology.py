"""Controlled ontology for semantic tagging of FOAs.

Each category maps a tag label to:
  - ``keywords``:  positive keywords that trigger the tag
  - ``negative``:  negative keywords that suppress a false-positive match
  - ``weight``:    multiplier for confidence scoring (default 1.0)
"""

ONTOLOGY: dict[str, dict[str, dict]] = {
    # ──────────────────────────────────────────────────────────────
    # Research domains
    # ──────────────────────────────────────────────────────────────
    "research_domains": {
        "machine_learning": {
            "keywords": [
                "machine learning", "deep learning", "neural network",
                "artificial intelligence", "reinforcement learning",
                "natural language processing", "nlp", "computer vision",
                "generative model", "large language model", "transformer",
            ],
            "negative": [],
        },
        "public_health": {
            "keywords": [
                "public health", "disease", "clinical trial", "epidemiology",
                "biomedical", "patient outcome", "cancer research",
                "mental health", "substance abuse", "maternal health",
            ],
            "negative": ["healthcare industry", "national security"],
        },
        "education": {
            "keywords": [
                "education", "learning outcomes", "curriculum",
                "stem education", "pedagogy", "K-12", "higher education",
                "teacher training", "educational technology",
            ],
            "negative": [],
        },
        "environment": {
            "keywords": [
                "environment", "climate change", "sustainability", "ecology",
                "carbon emission", "renewable energy", "biodiversity",
                "conservation", "water quality", "air quality",
            ],
            "negative": ["computing environment", "testing environment"],
        },
        "cybersecurity": {
            "keywords": [
                "cybersecurity", "network security", "privacy",
                "encryption", "vulnerability", "threat detection",
                "intrusion detection", "information security",
            ],
            "negative": ["national security commission"],
        },
        "social_science": {
            "keywords": [
                "social science", "behavioral science", "psychology",
                "community engagement", "equity", "diversity and inclusion",
                "economics", "political science", "sociology",
            ],
            "negative": [],
        },
        "engineering": {
            "keywords": [
                "engineering", "robotics", "manufacturing",
                "materials science", "mechanical engineering",
                "electrical engineering", "civil engineering",
                "aerospace", "nanotechnology",
            ],
            "negative": [],
        },
        "data_science": {
            "keywords": [
                "data science", "big data", "data analytics",
                "data visualization", "statistical analysis", "database",
                "data mining", "data engineering",
            ],
            "negative": [],
        },
        "biology": {
            "keywords": [
                "biology", "genomics", "proteomics", "molecular biology",
                "biotechnology", "bioinformatics", "cell biology",
                "neuroscience", "genetics",
            ],
            "negative": [],
        },
        "physics_astronomy": {
            "keywords": [
                "physics", "astronomy", "astrophysics", "quantum",
                "particle physics", "cosmology", "gravitational",
                "astronomical", "telescope",
            ],
            "negative": [],
        },
    },

    # ──────────────────────────────────────────────────────────────
    # Methods / approaches
    # ──────────────────────────────────────────────────────────────
    "methods": {
        "experimental": {
            "keywords": [
                "experiment", "randomized controlled trial", "lab study",
                "empirical study", "clinical trial", "field experiment",
            ],
            "negative": [],
        },
        "computational": {
            "keywords": [
                "computational", "simulation", "modeling", "algorithm",
                "software development", "numerical method", "high-performance computing",
            ],
            "negative": [],
        },
        "survey_qualitative": {
            "keywords": [
                "survey", "interview", "qualitative", "ethnography",
                "case study", "focus group", "participant observation",
            ],
            "negative": [],
        },
        "mixed_methods": {
            "keywords": [
                "mixed method", "quantitative and qualitative",
                "multi-method", "triangulation",
            ],
            "negative": [],
        },
        "data_driven": {
            "keywords": [
                "data-driven", "machine learning", "statistical learning",
                "predictive model", "data analysis pipeline",
            ],
            "negative": [],
        },
    },

    # ──────────────────────────────────────────────────────────────
    # Populations
    # ──────────────────────────────────────────────────────────────
    "populations": {
        "youth": {
            "keywords": [
                "youth", "children", "adolescent", "K-12",
                "undergraduate student", "young adult", "minor",
            ],
            "negative": [],
        },
        "underserved": {
            "keywords": [
                "underserved", "underrepresented", "low-income",
                "minority", "rural community", "disadvantaged",
                "limited resources", "marginalized",
            ],
            "negative": [],
        },
        "veterans": {
            "keywords": ["veteran", "military personnel", "armed forces", "service member"],
            "negative": [],
        },
        "elderly": {
            "keywords": ["elderly", "aging population", "older adult", "senior citizen", "geriatric"],
            "negative": ["senior personnel"],
        },
        "general_public": {
            "keywords": ["general public", "citizen science", "broad population", "community-based"],
            "negative": [],
        },
        "researchers": {
            "keywords": [
                "early-career", "principal investigator", "postdoctoral",
                "faculty", "graduate student", "research community",
            ],
            "negative": [],
        },
    },

    # ──────────────────────────────────────────────────────────────
    # Sponsor themes
    # ──────────────────────────────────────────────────────────────
    "sponsor_themes": {
        "workforce_development": {
            "keywords": [
                "workforce development", "job training", "career pathway",
                "employment", "skill development", "reskilling",
            ],
            "negative": [],
        },
        "innovation": {
            "keywords": [
                "innovation", "entrepreneurship", "startup",
                "commercialization", "technology transfer",
                "intellectual property",
            ],
            "negative": [],
        },
        "basic_research": {
            "keywords": [
                "basic research", "fundamental research", "discovery",
                "exploratory research", "curiosity-driven",
            ],
            "negative": [],
        },
        "applied_research": {
            "keywords": [
                "applied research", "translational research",
                "implementation science", "deployment", "real-world application",
            ],
            "negative": [],
        },
        "infrastructure": {
            "keywords": [
                "research infrastructure", "facility", "equipment",
                "instrumentation", "shared resource", "cyberinfrastructure",
            ],
            "negative": [],
        },
        "capacity_building": {
            "keywords": [
                "capacity building", "institutional development",
                "broadening participation", "training program",
                "research initiation",
            ],
            "negative": [],
        },
    },
}
