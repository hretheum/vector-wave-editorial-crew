#!/usr/bin/env python3
"""Test Resource-Aware Local Setup - Task 11.3"""

import sys
import os

sys.path.append('src')

from ai_writing_flow.optimization.resource_manager import (
    ResourceAwareManager,
    SystemResources,
    get_resource_manager,
    auto_configure_for_resources
)

def test_resource_aware_setup():
    """Test resource-aware local setup"""
    
    print("🧪 Testing Resource-Aware Local Setup - Task 11.3")
    print("=" * 60)
    
    # Test 1: Resource detection
    print("\n1️⃣ Testing resource detection...")
    try:
        manager = ResourceAwareManager()
        resources = manager.resources
        
        print("✅ System resources detected:")
        print(f"   CPU: {resources.cpu_count} cores @ {resources.cpu_freq_mhz:.0f}MHz")
        print(f"   Memory: {resources.memory_total_gb:.1f}GB total")
        print(f"   Memory Available: {resources.memory_available_gb:.1f}GB")
        print(f"   Disk Free: {resources.disk_free_gb:.1f}GB")
        print(f"   Platform: {resources.platform}")
        print(f"   Resource Tier: {resources.resource_tier}")
        
        assert resources.cpu_count > 0
        assert resources.memory_total_gb > 0
        assert resources.platform in ["Darwin", "Linux", "Windows"]
        
    except Exception as e:
        print(f"❌ Resource detection failed: {e}")
        return False
    
    # Test 2: Resource tier classification
    print("\n2️⃣ Testing resource tier classification...")
    try:
        # Test different resource configurations
        test_configs = [
            (2, 4.0, "low"),      # 2 cores, 4GB RAM = low
            (4, 8.0, "medium"),   # 4 cores, 8GB RAM = medium
            (8, 16.0, "high"),    # 8 cores, 16GB RAM = high
        ]
        
        for cpu, memory, expected_tier in test_configs:
            test_resources = SystemResources(
                cpu_count=cpu,
                cpu_freq_mhz=2000,
                memory_total_gb=memory,
                memory_available_gb=memory * 0.5,
                disk_free_gb=50,
                platform="Darwin",
                python_version="3.9.0"
            )
            
            tier = test_resources.resource_tier
            print(f"✅ {cpu} cores, {memory}GB RAM → {tier} tier")
            assert tier == expected_tier, f"Expected {expected_tier}, got {tier}"
        
    except Exception as e:
        print(f"❌ Tier classification failed: {e}")
        return False
    
    # Test 3: Configuration optimization
    print("\n3️⃣ Testing configuration optimization...")
    try:
        optimized_config = manager.get_optimized_config()
        tier = manager.resources.resource_tier
        
        print(f"✅ Optimized config for {tier} tier:")
        print(f"   Max concurrent agents: {optimized_config.get('max_concurrent_agents', 'default')}")
        print(f"   Model override: {optimized_config.get('model_override', 'default')}")
        print(f"   Cache TTL: {optimized_config.get('cache_ttl_seconds', 'default')}s")
        print(f"   Skip validation: {optimized_config.get('skip_validation', False)}")
        
        # Verify tier-appropriate settings
        if tier == "low":
            assert optimized_config["max_concurrent_agents"] == 1
            assert optimized_config["skip_validation"] == True
        elif tier == "high":
            assert optimized_config["max_concurrent_agents"] >= 4
            assert optimized_config["skip_validation"] == False
        
    except Exception as e:
        print(f"❌ Configuration optimization failed: {e}")
        return False
    
    # Test 4: Resource recommendations
    print("\n4️⃣ Testing resource recommendations...")
    try:
        recommendations = manager.get_recommendations()
        
        print(f"✅ Generated {len(recommendations)} recommendations")
        for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
            print(f"   {i}. {rec}")
        
        # Should always have some recommendations
        assert len(recommendations) > 0
        
    except Exception as e:
        print(f"❌ Recommendations test failed: {e}")
        return False
    
    # Test 5: Resource monitoring
    print("\n5️⃣ Testing resource monitoring...")
    try:
        metrics = manager.monitor_resources()
        
        print("✅ Current resource usage:")
        print(f"   CPU: {metrics['cpu_percent']:.1f}%")
        print(f"   Memory: {metrics['memory_percent']:.1f}%")
        print(f"   Memory Available: {metrics['memory_available_gb']:.1f}GB")
        
        assert "cpu_percent" in metrics
        assert "memory_percent" in metrics
        assert metrics["cpu_percent"] >= 0
        assert metrics["memory_percent"] >= 0
        
    except Exception as e:
        print(f"❌ Resource monitoring failed: {e}")
        return False
    
    # Test 6: Auto-configuration
    print("\n6️⃣ Testing auto-configuration...")
    try:
        # Apply auto-configuration
        applied_config = auto_configure_for_resources()
        
        print("✅ Auto-configuration applied")
        print(f"✅ {len(applied_config)} settings configured")
        
        # Check environment variables were set
        if "skip_validation" in applied_config:
            env_value = os.environ.get("SKIP_VALIDATION", "").lower()
            expected = str(applied_config["skip_validation"]).lower()
            assert env_value == expected
            print("✅ Environment variables updated correctly")
        
    except Exception as e:
        print(f"❌ Auto-configuration failed: {e}")
        return False
    
    # Test 7: Throttling detection
    print("\n7️⃣ Testing throttling detection...")
    try:
        should_throttle = manager.should_throttle()
        
        print(f"✅ Throttle recommendation: {should_throttle}")
        
        # This is informational - don't assert as it depends on current system state
        if should_throttle:
            print("   ⚠️  System resources are constrained")
        else:
            print("   ✅ System resources are adequate")
        
    except Exception as e:
        print(f"❌ Throttling detection failed: {e}")
        return False
    
    # Test 8: Print resource summary
    print("\n8️⃣ Testing resource summary display...")
    try:
        manager.print_resource_summary()
        print("✅ Resource summary displayed successfully")
        
    except Exception as e:
        print(f"❌ Resource summary failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Resource-Aware Setup tests passed!")
    print("✅ Task 11.3 implementation is complete")
    print("\nKey achievements:")
    print("- Automatic resource detection")
    print("- Dynamic tier classification")
    print("- Configuration optimization based on resources")
    print("- Performance recommendations")
    print("- Real-time resource monitoring")
    print("- Auto-configuration with environment variables")
    print("- Throttling detection")
    print("- Comprehensive resource reporting")
    print("\n✅ System adapts to different hardware configurations")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_resource_aware_setup()
    exit(0 if success else 1)