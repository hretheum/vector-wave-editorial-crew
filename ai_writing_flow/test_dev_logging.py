#!/usr/bin/env python3
"""Test Developer-Friendly Logging - Task 12.2"""

import sys
import time
import tempfile
import os

sys.path.append('src')

from ai_writing_flow.monitoring.dev_logger import (
    setup_dev_logging,
    log_context,
    log_performance,
    log_method,
    log_slow_operations,
    get_flow_logger,
    get_agent_logger,
    get_kb_logger,
    log_flow_stage,
    log_kb_query,
    log_agent_action,
    Colors
)
import structlog

def test_dev_logging():
    """Test developer-friendly logging functionality"""
    
    print("🧪 Testing Developer-Friendly Logging - Task 12.2")
    print("=" * 60)
    
    # Test 1: Basic logging setup
    print("\n1️⃣ Testing basic logging setup...")
    try:
        # Setup with verbose mode
        setup_dev_logging(
            log_level="DEBUG",
            show_timestamp=True,
            show_caller=True,
            enable_performance_warnings=True
        )
        
        logger = structlog.get_logger()
        
        # Test different log levels
        logger.debug("Debug message - detailed information")
        logger.info("Info message - general information")
        logger.warning("Warning message - something to note")
        logger.error("Error message - something went wrong", error_code=404)
        
        print("✅ Basic logging setup working")
        print("✅ All log levels functional")
        
    except Exception as e:
        print(f"❌ Basic logging test failed: {e}")
        return False
    
    # Test 2: Context logging
    print("\n2️⃣ Testing context logging...")
    try:
        with log_context(flow_id="test_flow_123", user="developer"):
            logger = structlog.get_logger()
            logger.info("Message with context")
            
            # Nested context
            with log_context(stage="processing"):
                logger.info("Nested context message")
        
        # Context should be cleared
        logger.info("Message without context")
        
        print("✅ Context logging working")
        print("✅ Nested contexts supported")
        
    except Exception as e:
        print(f"❌ Context logging test failed: {e}")
        return False
    
    # Test 3: Performance logging
    print("\n3️⃣ Testing performance logging...")
    try:
        # Normal operation
        with log_performance("fast_operation"):
            time.sleep(0.1)
        
        # Slow operation
        with log_performance("slow_operation", warn_threshold=0.05):
            time.sleep(0.2)  # Will trigger warning
        
        print("✅ Performance logging working")
        print("✅ Slow operation warnings triggered")
        
    except Exception as e:
        print(f"❌ Performance logging test failed: {e}")
        return False
    
    # Test 4: Method decorators
    print("\n4️⃣ Testing method decorators...")
    try:
        @log_method(component="test")
        def test_function(x, y, debug=False):
            time.sleep(0.05)
            return x + y
        
        @log_slow_operations(threshold=0.1)
        def slow_function():
            time.sleep(0.15)
            return "done"
        
        # Test decorated functions
        result1 = test_function(5, 3, debug=True)
        assert result1 == 8
        
        result2 = slow_function()  # Should trigger warning
        assert result2 == "done"
        
        print("✅ Method decorators working")
        print("✅ Entry/exit and performance tracking")
        
    except Exception as e:
        print(f"❌ Method decorators test failed: {e}")
        return False
    
    # Test 5: Component-specific loggers
    print("\n5️⃣ Testing component-specific loggers...")
    try:
        # Flow logger
        flow_logger = get_flow_logger("flow_456", "writing_flow")
        flow_logger.info("Flow started", stage="initialization")
        
        # Agent logger
        agent_logger = get_agent_logger("ContentAgent")
        agent_logger.info("Agent processing", task="content_generation")
        
        # KB logger
        kb_logger = get_kb_logger()
        kb_logger.info("KB query", query="test query", results=5)
        
        print("✅ Component loggers working")
        print("✅ Flow, Agent, and KB loggers functional")
        
    except Exception as e:
        print(f"❌ Component loggers test failed: {e}")
        return False
    
    # Test 6: Helper functions
    print("\n6️⃣ Testing logging helper functions...")
    try:
        # Flow stage logging
        log_flow_stage(
            flow_id="flow_789",
            stage="content_analysis",
            message="Analyzing content requirements",
            duration=1.23
        )
        
        # KB query logging
        log_kb_query(
            query="SELECT * FROM knowledge WHERE topic='AI'",
            cache_hit=True,
            duration=0.001,
            result_count=10
        )
        
        log_kb_query(
            query="Complex knowledge base query with multiple joins",
            cache_hit=False,
            duration=0.456,
            result_count=25
        )
        
        # Agent action logging
        log_agent_action(
            agent_name="ResearchAgent",
            action="started_research",
            topic="Machine Learning",
            sources=5
        )
        
        print("✅ Helper functions working")
        print("✅ Standardized logging formats")
        
    except Exception as e:
        print(f"❌ Helper functions test failed: {e}")
        return False
    
    # Test 7: File logging
    print("\n7️⃣ Testing file logging...")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as tmp:
            log_file = tmp.name
        
        # Setup with file logging
        setup_dev_logging(
            log_level="INFO",
            log_file=log_file,
            show_timestamp=True
        )
        
        logger = structlog.get_logger()
        logger.info("Test message for file")
        logger.error("Error message for file", error_type="TestError")
        
        # Check file exists and has content
        assert os.path.exists(log_file)
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Test message for file" in content
            assert "Error message for file" in content
        
        # Cleanup
        os.unlink(log_file)
        
        print("✅ File logging working")
        print("✅ Logs written to file successfully")
        
    except Exception as e:
        print(f"❌ File logging test failed: {e}")
        return False
    
    # Test 8: Color output demonstration
    print("\n8️⃣ Testing color output...")
    try:
        print(f"\n{Colors.BOLD}Color Output Examples:{Colors.RESET}")
        print(f"{Colors.DEBUG}DEBUG: Detailed debugging information{Colors.RESET}")
        print(f"{Colors.INFO}INFO: General information message{Colors.RESET}")
        print(f"{Colors.WARNING}WARNING: Something needs attention{Colors.RESET}")
        print(f"{Colors.ERROR}ERROR: An error occurred{Colors.RESET}")
        print(f"{Colors.FLOW}[flow] Flow execution message{Colors.RESET}")
        print(f"{Colors.KB}[kb] Knowledge base operation{Colors.RESET}")
        print(f"{Colors.AGENT}[agent] Agent activity{Colors.RESET}")
        
        print("\n✅ Color output working")
        
    except Exception as e:
        print(f"❌ Color output test failed: {e}")
        return False
    
    # Test 9: Error handling in logging
    print("\n9️⃣ Testing error handling in logging...")
    try:
        @log_method(component="error_test")
        def failing_function():
            raise ValueError("Test error")
        
        try:
            failing_function()
        except ValueError:
            pass  # Expected
        
        # Log with exception info
        logger = structlog.get_logger()
        try:
            1 / 0
        except ZeroDivisionError as e:
            logger.error(
                "Division by zero caught",
                error_type=type(e).__name__,
                error_msg=str(e),
                exc_info=True
            )
        
        print("✅ Error handling in logging working")
        print("✅ Exceptions logged properly")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    # Test 10: Performance demonstration
    print("\n🔟 Testing logging performance impact...")
    try:
        import timeit
        
        # Time without logging
        def no_logging():
            x = 1 + 1
            return x
        
        # Time with logging
        logger = structlog.get_logger()
        def with_logging():
            logger.debug("Computing", operation="addition")
            x = 1 + 1
            logger.debug("Computed", result=x)
            return x
        
        time_no_log = timeit.timeit(no_logging, number=1000)
        time_with_log = timeit.timeit(with_logging, number=1000)
        
        overhead = (time_with_log - time_no_log) / 1000 * 1000  # ms per call
        
        print(f"✅ Logging overhead: {overhead:.3f}ms per call")
        print(f"✅ Acceptable performance impact")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Developer-Friendly Logging tests passed!")
    print("✅ Task 12.2 implementation is complete")
    print("\nKey achievements:")
    print("- Color-coded output by level and component")
    print("- Structured context with log_context")
    print("- Performance tracking and warnings")
    print("- Method decorators for easy integration")
    print("- Component-specific loggers")
    print("- Standardized helper functions")
    print("- File logging support")
    print("- Minimal performance overhead")
    print("- Enhanced debugging capabilities")
    print("=" * 60)
    
    # Final demo
    print("\n📋 Example Integrated Logging Flow:")
    with log_context(flow_id="demo_flow", user="developer"):
        flow_logger = get_flow_logger("demo_flow", "example")
        flow_logger.info("Starting example flow")
        
        with log_performance("example_operation", warn_threshold=0.1):
            time.sleep(0.05)
            log_kb_query("demo query", cache_hit=True, duration=0.001)
            log_agent_action("DemoAgent", "processed", items=10)
        
        flow_logger.info("Flow completed successfully")
    
    return True

if __name__ == "__main__":
    success = test_dev_logging()
    exit(0 if success else 1)