from typing import List, Optional
from datetime import datetime
from app.services.crud_user import user as user_crud
from app.services.crud_interview import interview as interview_crud
from app.schemas_api.user import UserCreate, UserUpdate
from app.schemas_api.interview import InterviewCreate
from app.schemas_db.user import User, SubjectProgress

class InterviewService:
    async def get_or_create_user(self, email: str, nickname: str) -> User:
        """
        Retrieves a user by email or creates a new one if not exists.
        For guest access, email can be auto-generated.
        """
        existing_user = await user_crud.get_by_email(email)
        if existing_user:
            return existing_user
        
        # Create new user
        # Direct DB structure mapping since UserCreate is flat API schema
        user_in_data = {
            "auth": {
                "email": email,
                "provider": "guest",
                "uid": email
            },
            "profile": {
                "nickname": nickname,
                "avatar_url": None,
                "job_title": "Guest User"
            }
        }
        
        created_user = await user_crud.create(user_in_data)
        return created_user

    async def update_skill_status(self, user_id: str, subject: str, passed: bool, score: int) -> bool:
        """
        Updates the user's skill status based on interview performance.
        Returns True if a Star was granted, False otherwise.
        """
        user = await user_crud.get(user_id)
        if not user:
            return False
        
        star_granted = False
        
        # 1. Update Skill Tree
        skills = user.skill_tree
        if subject not in skills:
            skills[subject] = SubjectProgress()
            
        progress = skills[subject]
        progress.last_tested_at = datetime.utcnow()
        
        # Simple Logic: Grant Star if Score >= 80 (or passed)
        # v1.1 Rule: Reward logic could be complex, but here we use simple threshold
        if passed and score >= 70:
            progress.stars += 1
            user.stats.total_stars += 1
            star_granted = True
            
            # Level Up Logic (Mock: 3 stars -> Next Level)
            if progress.stars >= 3 and progress.level < 3:
                progress.level += 1
                
        # 2. Update User DB
        # We need to serialize Pydantic models to dicts for MongoDB
        skills_dict = {k: v.dict() for k, v in skills.items()}
        
        update_data = {
            "skill_tree": skills_dict,
            "stats": user.stats.dict(),
            "updated_at": datetime.utcnow()
        }
        
        await user_crud.update(user_id, update_data)
        
        return star_granted

    async def save_questions(self, questions: List[dict]):
        """
        Batch saves generated questions to the database (Asset DB).
        Not fully implemented in MVP, just a placeholder.
        """
        pass
    
    async def get_user_state(self, user_id: str) -> dict:
        """
        Returns a simplified state dict for the agent.
        """
        user = await user_crud.get(user_id)
        if not user:
            return {}
        
        return {
            "nickname": user.profile.nickname,
            "total_stars": user.stats.total_stars,
            "recent_skills": {k: v.dict() for k, v in list(user.skill_tree.items())[:5]}
        }

interview_service = InterviewService()
