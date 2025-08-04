from app import create_app, db
from app.models import School, Chapter

app = create_app()

with app.app_context():
    # Create FSU
    fsu = School.query.filter_by(domain="fsu.edu").first()
    if not fsu:
        fsu = School(name="Florida State University", domain="fsu.edu")
        db.session.add(fsu)
        db.session.commit()

    # FSU Fraternities
    fraternities = [
        "Sigma Phi Epsilon (Sigep)",
        "Pi Kappa Alpha (Pike)",
        "Theta Chi",
        "Kappa Alpha",
        "Kappa Sigma",
        "Delta Chi",
        "Beta Theta Pi (Beta)",
        "Sigma Chi",
        "Phi Gamma Delta (FIJI)"
    ]

    # FSU Sororities
    sororities = [
        "Alpha Delta Pi (ADPi)",
        "Delta Delta Delta (Tridelt)",
        "Zeta Tau Alpha (Zeta)",
        "Delta Gamma (DG)",
        "Kappa Alpha Theta (Theta)",
        "Chi Omega (Chi O)",
        "Sigma Delta Tau (Sig Delt)",
        "Kappa Kappa Gamma",
        "Alpha Gamma Delta",
        "Alpha Chi Omega",
        "Delta Zeta",
        "Phi Mu",
        "Alpha Phi"
    ]

    # Insert Fraternities
    for name in fraternities:
        chapter = Chapter(name=name, type="Fraternity", school_id=fsu.school_id, verified=True)
        db.session.add(chapter)

    # Insert Sororities
    for name in sororities:
        chapter = Chapter(name=name, type="Sorority", school_id=fsu.school_id, verified=True)
        db.session.add(chapter)

    db.session.commit()
    print("✅ Seeded FSU and chapters successfully.")
