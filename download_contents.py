import os
import logging

import cyworld

logging.basicConfig(level=logging.WARNING)

if __name__ == "__main__":
    EMAIL = os.environ["CYWORLD_EMAIL"]
    PASSWORD = os.environ["CYWORLD_PASSWORD"]

    cy = cyworld.Cyworld()
    cy.login(email=EMAIL, password=PASSWORD)
    cy.move_to_home()
    cy.download_all_contents()
