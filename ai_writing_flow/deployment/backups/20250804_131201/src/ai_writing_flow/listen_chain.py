"""
Listen Chain Replacement - replaces @listen decorator pattern

This module implements linear method chaining to replace CrewAI's @listen decorators,
ensuring no circular dependencies and proper execution order.
"""

import logging
from typing import Dict, Any, Optional, Callable, List, Union
from datetime import datetime, timezone

from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.models.flow_control_state import FlowControlState
from ai_writing_flow.managers.stage_manager import StageManager
from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker
from ai_writing_flow.flow_inputs import FlowPathConfig

logger = logging.getLogger(__name__)


class ChainExecutionResult:
    """Result of chain method execution"""
    
    def __init__(self):
        self.success: bool = False
        self.next_method: Optional[str] = None
        self.data: Dict[str, Any] = {}
        self.should_continue: bool = True
        self.error_message: Optional[str] = None
        self.execution_time: Optional[datetime] = None
        self.retry_count: int = 0
        self.fallback_used: bool = False


class LinearExecutionChain:
    """
    Linear execution chain replacing @listen decorator pattern
    
    Features:
    - No circular dependencies through explicit method chaining
    - State-based routing decisions  
    - Standardized return value patterns
    - Conditional execution logic
    - Clear start-to-end execution path
    """
    
    def __init__(
        self,
        stage_manager: StageManager,
        circuit_breaker: StageCircuitBreaker,
        config: FlowPathConfig
    ):
        self.stage_manager = stage_manager
        self.circuit_breaker = circuit_breaker
        self.config = config
        self._execution_history: List[Dict[str, Any]] = []
        self._current_chain_step = 0
        
        # Define the linear execution flow (Task 15.1)
        self._execution_chain = self._build_execution_chain()
    
    def _build_execution_chain(self) -> List[Dict[str, Any]]:
        """
        Build complete linear execution flow - Task 15.1
        
        Returns:
            List of execution steps with method names and conditions
        """
        
        chain = []
        
        # Step 1: Input Validation (always first)
        chain.append({
            "method": "validate_inputs",
            "stage": FlowStage.INPUT_VALIDATION,
            "condition": lambda state: True,  # Always execute
            "next_on_success": "conduct_research",
            "next_on_skip": "align_audience",
            "max_retries": 0
        })
        
        # Step 2: Research (conditional)
        chain.append({
            "method": "conduct_research", 
            "stage": FlowStage.RESEARCH,
            "condition": lambda state: not self.config.skip_research and state.content_ownership != "ORIGINAL",
            "next_on_success": "align_audience",
            "next_on_skip": "align_audience",
            "max_retries": self.config.research_max_retries
        })
        
        # Step 3: Audience Alignment
        chain.append({
            "method": "align_audience",
            "stage": FlowStage.AUDIENCE_ALIGN, 
            "condition": lambda state: not self.config.skip_audience_alignment,
            "next_on_success": "generate_draft",
            "next_on_skip": "generate_draft",
            "max_retries": self.config.audience_max_retries
        })
        
        # Step 4: Draft Generation
        chain.append({
            "method": "generate_draft",
            "stage": FlowStage.DRAFT_GENERATION,
            "condition": lambda state: True,  # Always needed
            "next_on_success": "validate_style",
            "next_on_skip": "validate_style", 
            "max_retries": self.config.draft_max_retries
        })
        
        # Step 5: Style Validation
        chain.append({
            "method": "validate_style",
            "stage": FlowStage.STYLE_VALIDATION,
            "condition": lambda state: not self.config.skip_style_validation,
            "next_on_success": "assess_quality",
            "next_on_skip": "assess_quality",
            "max_retries": self.config.style_max_retries
        })
        
        # Step 6: Quality Assessment (final step)
        chain.append({
            "method": "assess_quality",
            "stage": FlowStage.QUALITY_CHECK,
            "condition": lambda state: not self.config.skip_quality_check,
            "next_on_success": "finalize",
            "next_on_skip": "finalize",
            "max_retries": self.config.quality_max_retries
        })
        
        # Step 7: Finalization (always last)
        chain.append({
            "method": "finalize",
            "stage": FlowStage.FINALIZED,
            "condition": lambda state: True,  # Always execute
            "next_on_success": None,  # End of chain
            "next_on_skip": None,
            "max_retries": 0
        })
        
        logger.info(f"📋 Built execution chain with {len(chain)} steps")
        return chain
    
    def execute_chain(self, writing_state, method_implementations: Dict[str, Callable]) -> ChainExecutionResult:
        """
        Execute the complete linear chain
        
        Args:
            writing_state: Current WritingFlowState
            method_implementations: Dict mapping method names to actual implementations
            
        Returns:
            ChainExecutionResult with final execution status
        """
        
        logger.info("🚀 Starting linear execution chain...")
        
        result = ChainExecutionResult()
        result.execution_time = datetime.now(timezone.utc)
        
        try:
            # Execute each step in the chain
            for step_index, step_config in enumerate(self._execution_chain):
                self._current_chain_step = step_index
                
                # Check if step should be executed
                if not step_config["condition"](writing_state):
                    logger.info(f"⏭️ Skipping step {step_index}: {step_config['method']}")
                    self._log_execution_step(step_config["method"], "SKIPPED", writing_state)
                    continue
                
                # Execute the step
                step_result = self._execute_chain_step(
                    step_config, 
                    writing_state, 
                    method_implementations
                )
                
                # Store execution history
                self._log_execution_step(
                    step_config["method"], 
                    "SUCCESS" if step_result.success else "FAILED",
                    writing_state,
                    step_result
                )
                
                # Check if step failed and we can't continue
                if not step_result.success and not step_result.should_continue:
                    result.success = False
                    result.error_message = f"Chain stopped at step {step_index}: {step_result.error_message}"
                    logger.error(f"❌ Chain execution failed at {step_config['method']}: {step_result.error_message}")
                    return result
                
                # Update overall result data
                result.data.update(step_result.data)
            
            # Chain completed successfully
            result.success = True
            result.next_method = None  # Chain is complete
            
            logger.info("✅ Linear execution chain completed successfully")
            return result
            
        except Exception as e:
            result.success = False
            result.error_message = f"Chain execution exception: {str(e)}"
            logger.error(f"❌ Chain execution failed with exception: {str(e)}", exc_info=True)
            return result
    
    def _execute_chain_step(
        self, 
        step_config: Dict[str, Any], 
        writing_state, 
        method_implementations: Dict[str, Callable]
    ) -> ChainExecutionResult:
        """
        Execute a single step in the chain with retry logic
        
        Args:
            step_config: Configuration for this chain step
            writing_state: Current WritingFlowState  
            method_implementations: Available method implementations
            
        Returns:
            ChainExecutionResult for this step
        """
        
        method_name = step_config["method"]
        max_retries = step_config["max_retries"]
        
        logger.info(f"🔄 Executing chain step: {method_name}")
        
        # Check if method implementation exists
        if method_name not in method_implementations:
            result = ChainExecutionResult()
            result.success = False
            result.should_continue = False
            result.error_message = f"Method implementation not found: {method_name}"
            return result
        
        method_impl = method_implementations[method_name]
        
        # Execute with retry logic
        for retry_count in range(max_retries + 1):
            try:
                # Execute with circuit breaker protection
                execution_result = self.circuit_breaker.call(
                    method_impl,
                    writing_state=writing_state
                )
                
                # Convert to ChainExecutionResult
                result = self._convert_to_chain_result(execution_result, step_config)
                result.retry_count = retry_count
                
                if result.success:
                    logger.info(f"✅ Step {method_name} completed successfully")
                    return result
                elif retry_count < max_retries:
                    logger.warning(f"🔄 Step {method_name} failed, retrying... ({retry_count + 1}/{max_retries})")
                    continue
                else:
                    logger.error(f"❌ Step {method_name} failed after {max_retries} retries")
                    result.should_continue = self._should_continue_after_failure(step_config, result)
                    return result
                    
            except Exception as e:
                logger.error(f"❌ Step {method_name} exception on retry {retry_count}: {str(e)}")
                
                if retry_count < max_retries:
                    continue
                else:
                    # Final failure
                    result = ChainExecutionResult()
                    result.success = False
                    result.error_message = f"Step failed after {max_retries} retries: {str(e)}"
                    result.retry_count = retry_count
                    result.should_continue = self._should_continue_after_failure(step_config, result)
                    return result
    
    def _convert_to_chain_result(self, execution_result: Any, step_config: Dict[str, Any]) -> ChainExecutionResult:
        """
        Convert method execution result to standardized ChainExecutionResult - Task 15.2
        
        Args:
            execution_result: Result from method execution
            step_config: Configuration for this step
            
        Returns:
            Standardized ChainExecutionResult
        """
        
        result = ChainExecutionResult()
        
        # Handle different result types
        if hasattr(execution_result, 'success'):
            result.success = execution_result.success
        elif hasattr(execution_result, 'completion_time'):
            result.success = True  # If it has completion_time, assume success
        elif execution_result is True:
            result.success = True
        elif execution_result is False:
            result.success = False
        else:
            result.success = execution_result is not None
        
        # Determine next method based on success - Task 15.3
        if result.success:
            result.next_method = step_config.get("next_on_success")
        else:
            result.next_method = step_config.get("next_on_skip")
        
        # Extract data from result
        if hasattr(execution_result, '__dict__'):
            result.data = {k: v for k, v in execution_result.__dict__.items() 
                          if not k.startswith('_')}
        
        result.execution_time = datetime.now(timezone.utc)
        
        return result
    
    def _should_continue_after_failure(self, step_config: Dict[str, Any], result: ChainExecutionResult) -> bool:
        """
        Determine if chain should continue after step failure - Task 15.3
        
        Args:
            step_config: Configuration for the failed step
            result: Execution result of the failed step
            
        Returns:
            True if chain should continue despite failure
        """
        
        method_name = step_config["method"]
        
        # Critical steps that must succeed
        critical_steps = ["validate_inputs", "finalize"]
        if method_name in critical_steps:
            logger.warning(f"🚨 Critical step {method_name} failed - stopping chain")
            return False
        
        # Optional steps can be skipped
        optional_steps = ["conduct_research", "validate_style"]
        if method_name in optional_steps:
            logger.info(f"⏭️ Optional step {method_name} failed - continuing chain")
            return True
        
        # For other steps, continue if we have a fallback
        if result.fallback_used:
            logger.info(f"🔄 Step {method_name} failed but fallback used - continuing chain")
            return True
        
        # Default: continue for non-critical failures
        logger.warning(f"⚠️ Step {method_name} failed - continuing chain with degraded functionality")
        return True
    
    def _log_execution_step(
        self, 
        method_name: str, 
        status: str, 
        writing_state, 
        result: Optional[ChainExecutionResult] = None
    ) -> None:
        """Log execution step for debugging and monitoring"""
        
        step_log = {
            "method": method_name,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chain_position": self._current_chain_step,
            "writing_state_stage": writing_state.current_stage,
            "retry_count": result.retry_count if result else 0,
            "fallback_used": result.fallback_used if result else False
        }
        
        self._execution_history.append(step_log)
        
        logger.info(f"📝 Chain step logged: {method_name} -> {status}")
    
    def get_execution_status(self) -> Dict[str, Any]:
        """
        Get comprehensive execution chain status
        
        Returns:
            Dict with chain execution status
        """
        
        total_steps = len(self._execution_chain)
        completed_steps = len([h for h in self._execution_history if h["status"] in ["SUCCESS", "SKIPPED"]])
        failed_steps = len([h for h in self._execution_history if h["status"] == "FAILED"])
        
        return {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "current_step": self._current_chain_step,
            "progress_percentage": (completed_steps / total_steps * 100) if total_steps > 0 else 0,
            "execution_history": self._execution_history,
            "chain_configuration": [
                {
                    "method": step["method"],
                    "stage": step["stage"].value,
                    "max_retries": step["max_retries"]
                }
                for step in self._execution_chain
            ]
        }
    
    def get_next_method(self, current_method: str, success: bool) -> Optional[str]:
        """
        Get next method in chain based on current method and success state - Task 15.2
        
        Args:
            current_method: Name of current method
            success: Whether current method succeeded
            
        Returns:
            Name of next method or None if chain complete
        """
        
        # Find current step in chain
        for step in self._execution_chain:
            if step["method"] == current_method:
                if success:
                    return step.get("next_on_success")
                else:
                    return step.get("next_on_skip")
        
        logger.warning(f"⚠️ Method {current_method} not found in execution chain")
        return None
    
    def validate_chain_configuration(self) -> Dict[str, Any]:
        """
        Validate the execution chain configuration
        
        Returns:
            Validation results
        """
        
        issues = []
        warnings = []
        
        # Check for circular references
        method_names = [step["method"] for step in self._execution_chain]
        if len(method_names) != len(set(method_names)):
            issues.append("Duplicate method names in chain")
        
        # Check next method references
        for step in self._execution_chain:
            next_success = step.get("next_on_success")
            next_skip = step.get("next_on_skip")
            
            if next_success and next_success not in method_names and next_success != "finalize":
                warnings.append(f"next_on_success '{next_success}' not found in chain for {step['method']}")
            
            if next_skip and next_skip not in method_names and next_skip != "finalize":
                warnings.append(f"next_on_skip '{next_skip}' not found in chain for {step['method']}")
        
        # Check retry limits
        for step in self._execution_chain:
            if step["max_retries"] > 10:
                warnings.append(f"High retry count ({step['max_retries']}) for {step['method']}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_steps": len(self._execution_chain),
            "chain_length_ok": len(self._execution_chain) <= 20
        }


# Export main classes
__all__ = [
    "LinearExecutionChain",
    "ChainExecutionResult"
]