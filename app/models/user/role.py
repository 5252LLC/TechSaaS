"""
Role Model

This module defines the Role model for user permissions.
"""

from app import db

class Role(db.Model):
    """
    Role model for user permissions.
    
    TEACHING POINT:
    Separate roles from the user model allows for more flexible permission systems.
    A user can be assigned to one or more roles, and each role can have specific permissions.
    """
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))
    
    # Define permissions as bit values
    # Each permission is a bit flag that can be toggled on or off
    # 0x01: read, 0x02: write, 0x04: delete, 0x08: admin
    permissions = db.Column(db.Integer, default=0x01)  # Default to read-only
    
    # Define default roles as class attributes
    ROLE_USER = 'user'            # Regular user with basic permissions
    ROLE_MODERATOR = 'moderator'  # Can moderate content
    ROLE_ADMIN = 'admin'          # Has all permissions
    
    # Define permission bits
    PERMISSION_READ = 0x01
    PERMISSION_WRITE = 0x02
    PERMISSION_DELETE = 0x04
    PERMISSION_ADMIN = 0x08
    
    @staticmethod
    def insert_roles():
        """
        Create or update default roles in the database.
        """
        roles = {
            Role.ROLE_USER: {
                'description': 'Regular user with basic access',
                'permissions': Role.PERMISSION_READ
            },
            Role.ROLE_MODERATOR: {
                'description': 'Moderator with content management privileges',
                'permissions': Role.PERMISSION_READ | Role.PERMISSION_WRITE
            },
            Role.ROLE_ADMIN: {
                'description': 'Administrator with full access',
                'permissions': Role.PERMISSION_READ | Role.PERMISSION_WRITE | Role.PERMISSION_DELETE | Role.PERMISSION_ADMIN
            }
        }
        
        for role_name, role_info in roles.items():
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
            role.description = role_info['description']
            role.permissions = role_info['permissions']
            db.session.add(role)
        db.session.commit()
    
    def has_permission(self, permission):
        """
        Check if the role has a specific permission.
        
        Args:
            permission: Permission bit to check
            
        Returns:
            Boolean indicating if the role has the permission
        """
        return (self.permissions & permission) == permission
    
    def __repr__(self):
        return f'<Role {self.name}>'
