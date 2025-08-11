#!/usr/bin/env python3
"""
Script to initialize and test the Redis database connection.
"""

import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_redis_connection():
    """Test basic Redis connection."""
    try:
        import redis
        redis_url = os.getenv("REDIS_OM_URL", "redis://localhost:6379")
        print(f"Testing Redis connection to: {redis_url}")
        
        client = redis.from_url(redis_url)
        client.ping()
        print("✅ Redis server is running and accessible")
        
        # Test basic operations
        client.set("test_key", "test_value")
        value = client.get("test_key")
        client.delete("test_key")
        
        if value.decode() == "test_value":
            print("✅ Redis read/write operations working")
        
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def test_redis_om():
    """Test Redis OM (Object Mapping) functionality."""
    try:
        from redis_om import JsonModel, Migrator
        from sotopia.database import EpisodeLog, AgentProfile, EnvironmentProfile
        
        print("Testing Redis OM initialization...")
        
        # Run migrations
        try:
            Migrator().run()
            print("✅ Database migrations completed")
        except Exception as e:
            print(f"⚠️  Migration warning: {e}")
        
        # Test model queries
        try:
            episodes = EpisodeLog.find().all()
            print(f"✅ EpisodeLog model working - found {len(episodes)} episodes")
        except Exception as e:
            print(f"⚠️  EpisodeLog query failed: {e}")
        
        try:
            agents = AgentProfile.find().all()
            print(f"✅ AgentProfile model working - found {len(agents)} agents")
        except Exception as e:
            print(f"⚠️  AgentProfile query failed: {e}")
            
        try:
            environments = EnvironmentProfile.find().all()
            print(f"✅ EnvironmentProfile model working - found {len(environments)} environments")
        except Exception as e:
            print(f"⚠️  EnvironmentProfile query failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis OM initialization failed: {e}")
        return False


def show_database_info():
    """Show information about the current database."""
    try:
        import redis
        redis_url = os.getenv("REDIS_OM_URL", "redis://localhost:6379")
        client = redis.from_url(redis_url)
        
        # Get Redis info
        info = client.info()
        print(f"\n📊 Redis Database Information:")
        print(f"Redis version: {info.get('redis_version', 'Unknown')}")
        print(f"Used memory: {info.get('used_memory_human', 'Unknown')}")
        print(f"Connected clients: {info.get('connected_clients', 'Unknown')}")
        print(f"Total keys: {client.dbsize()}")
        
        # List some key patterns
        keys = client.keys("*")
        if keys:
            print(f"\nSample keys (first 10):")
            for key in keys[:10]:
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                print(f"  {key_str}")
        else:
            print("No keys found in database")
            
    except Exception as e:
        print(f"Error getting database info: {e}")


def main():
    print("🔍 Sotopia Database Initialization & Test")
    print("=" * 50)
    
    # Test basic Redis connection
    if not test_redis_connection():
        print("Basic Redis connection failed. Exiting.")
        return
    
    # Test Redis OM
    if not test_redis_om():
        print("Redis OM has issues, but basic Redis works.")
    
    # Show database info
    show_database_info()
    
    print("\n✅ Database initialization complete!")
    print("You can now use the database access scripts:")
    print("  python scripts/browse_database.py")
    print("  python scripts/access_user_study_data.py")


if __name__ == "__main__":
    main()