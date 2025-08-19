from typing import List

from sqlalchemy.orm import Session

from src.app.models.addon import Addon
from src.app.schemas.addon import AddonCreate, AddonUpdate


def create_addon(db: Session, addon: AddonCreate):
    new_addon = Addon(**addon.model_dump())
    db.add(new_addon)
    db.commit()
    db.refresh(new_addon)
    return new_addon


def get_addon(db: Session, addon_id: int):
    return db.query(Addon).filter(Addon.id == addon_id).first()


def get_addons(db: Session):
    return db.query(Addon).all()


def update_addon(db: Session, addon_id: int, updated_data: AddonUpdate):
    addon = get_addon(db, addon_id)
    if addon:
        # Only update fields that are provided (not None)
        update_dict = updated_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(addon, key, value)
        db.commit()
        db.refresh(addon)
    return addon


def delete_addon(db: Session, addon_id: int):
    addon = get_addon(db, addon_id)
    if addon:
        db.delete(addon)
        db.commit()
        return True
    return False
