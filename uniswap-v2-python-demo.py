# -*- coding: utf-8 -*-
"""
Uniswap V2 AMM Pool Implementation - Python 3 Compatible Version with Type Hints
兼容Python 3.6+的Uniswap V2自动做市商实现，包含完整类型注解
"""

from typing import Dict, Tuple, Union, Optional


class UniswapV2Pool:
    """
    Uniswap V2 自动做市商(AMM)流动性池实现 - 带类型注解版本
    基于恒定乘积公式: x * y = k
    """
    
    def __init__(self) -> None:
        """初始化流动性池"""
        self.reserve0: int = 0  # 代币0的储备量
        self.reserve1: int = 0  # 代币1的储备量
        self.total_liquidity: int = 0  # 流动性池的总流动性份额
        self.liquidity_providers: Dict[str, int] = {}  # 记录流动性提供者及其对应的流动性份额
        self.MINIMUM_LIQUIDITY: int = 1000  # 最小流动性锁定，防止恶意操作
        self.FEE_DENOMINATOR: int = 1000  # 手续费分母
        self.FEE_NUMERATOR: int = 997  # 手续费分子 (1000-3 = 997, 表示0.3%手续费)

    def initialize_pool(self, amount0: int, amount1: int, provider: str) -> int:
        """
        初始化流动性池
        
        功能: 为空的流动性池提供初始流动性，建立两种代币的初始比例
        AMM公式依据:
        - 初始流动性计算: L = sqrt(x * y)
        - 建立初始恒定乘积: k = x * y
        
        参数:
        - amount0: 代币0的初始投入量
        - amount1: 代币1的初始投入量
        - provider: 流动性提供者地址
        
        返回: 用户获得的流动性份额
        """
        # 输入验证
        if not isinstance(amount0, int) or not isinstance(amount1, int):
            raise TypeError("金额必须是整数")
        if not isinstance(provider, str):
            raise TypeError("提供者地址必须是字符串")
            
        if self.total_liquidity != 0:
            raise AssertionError("池已初始化")
        if amount0 <= 0 or amount1 <= 0:
            raise AssertionError("初始化金额必须大于0")
            
        # 计算初始流动性
        liquidity_squared: int = amount0 * amount1
        if liquidity_squared < self.MINIMUM_LIQUIDITY * self.MINIMUM_LIQUIDITY:
            raise AssertionError("初始流动性太小，至少需要 {}".format(self.MINIMUM_LIQUIDITY))
        
        # 使用整数平方根避免浮点数问题
        liquidity: int = int(liquidity_squared ** 0.5)
        if liquidity <= self.MINIMUM_LIQUIDITY:
            raise AssertionError("流动性计算结果太小")
        
        # 设置储备
        self.reserve0 = amount0
        self.reserve1 = amount1
        
        # 锁定最小流动性，给特殊地址（永久锁定）
        self.total_liquidity = liquidity
        user_liquidity: int = liquidity - self.MINIMUM_LIQUIDITY
        
        self.liquidity_providers['LOCKED'] = self.MINIMUM_LIQUIDITY
        self.liquidity_providers[provider] = user_liquidity
        
        return user_liquidity

    def add_liquidity(self, amount0: int, amount1: int, provider: str) -> Tuple[int, int, int, int, int]:
        """
        增加流动性
        
        功能: 向现有流动性池添加流动性，取较小的份额比例，多余代币退还
        
        参数:
        - amount0: 用户提供的代币0数量
        - amount1: 用户提供的代币1数量
        - provider: 流动性提供者地址
        
        返回: (liquidity, actual_amount0, actual_amount1, refund0, refund1)
        """
        # 输入验证
        if not isinstance(amount0, int) or not isinstance(amount1, int):
            raise TypeError("金额必须是整数")
        if not isinstance(provider, str):
            raise TypeError("提供者地址必须是字符串")
            
        if amount0 <= 0 or amount1 <= 0:
            raise AssertionError("添加金额必须大于0")
        if self.reserve0 <= 0 or self.reserve1 <= 0:
            raise AssertionError("池未初始化")
        if self.total_liquidity <= 0:
            raise AssertionError("总流动性异常")
        
        # 使用整数运算避免精度问题
        share0: int = (amount0 * self.total_liquidity) // self.reserve0
        share1: int = (amount1 * self.total_liquidity) // self.reserve1
        
        # 取较小份额
        min_share: int = min(share0, share1)
        if min_share <= 0:
            raise AssertionError("流动性太小，无法添加")
        
        # 根据较小份额计算实际使用金额
        actual_amount0: int = (min_share * self.reserve0) // self.total_liquidity
        actual_amount1: int = (min_share * self.reserve1) // self.total_liquidity
        
        # 计算退还金额
        refund0: int = amount0 - actual_amount0
        refund1: int = amount1 - actual_amount1
        
        # 更新状态
        liquidity: int = min_share
        self.reserve0 += actual_amount0
        self.reserve1 += actual_amount1
        self.total_liquidity += liquidity
        
        if provider not in self.liquidity_providers:
            self.liquidity_providers[provider] = 0
        self.liquidity_providers[provider] += liquidity
        
        return liquidity, actual_amount0, actual_amount1, refund0, refund1

    def remove_liquidity(self, liquidity: int, provider: str) -> Tuple[int, int]:
        """
        移除流动性
        
        功能: 从流动性池中移除指定份额的流动性，按比例取回两种代币
        
        参数:
        - liquidity: 要移除的流动性份额
        - provider: 流动性提供者地址
        
        返回: (amount0, amount1) 取回的代币数量
        """
        # 输入验证
        if not isinstance(liquidity, int):
            raise TypeError("流动性份额必须是整数")
        if not isinstance(provider, str):
            raise TypeError("提供者地址必须是字符串")
            
        if liquidity <= 0:
            raise AssertionError("移除的流动性必须大于0")
        if self.total_liquidity <= 0:
            raise AssertionError("池中无流动性")
        
        provider_liquidity: int = self.liquidity_providers.get(provider, 0)
        if provider_liquidity < liquidity:
            raise AssertionError("流动性份额不足")
        
        # 确保移除后仍有足够的总流动性
        remaining_liquidity: int = self.total_liquidity - liquidity
        if remaining_liquidity < self.MINIMUM_LIQUIDITY:
            raise AssertionError("不能移除过多流动性，必须保留最小流动性")
        
        # 计算取回金额
        amount0: int = (liquidity * self.reserve0) // self.total_liquidity
        amount1: int = (liquidity * self.reserve1) // self.total_liquidity
        
        # 更新状态
        self.reserve0 -= amount0
        self.reserve1 -= amount1
        self.total_liquidity -= liquidity
        self.liquidity_providers[provider] -= liquidity
        
        return amount0, amount1

    def swap(self, token_in: int, amount_in: int) -> int:
        """
        代币交换
        
        功能: 使用恒定乘积公式进行代币交换，正确处理交易手续费
        
        参数:
        - token_in: 输入代币类型 (0 或 1)
        - amount_in: 输入代币数量
        
        返回: 输出代币数量
        """
        # 输入验证
        if not isinstance(token_in, int) or token_in not in [0, 1]:
            raise TypeError("token_in必须是0或1")
        if not isinstance(amount_in, int):
            raise TypeError("输入金额必须是整数")
            
        if amount_in <= 0:
            raise AssertionError("输入金额必须大于0")
        if self.reserve0 <= 0 or self.reserve1 <= 0:
            raise AssertionError("池未初始化")
        
        if token_in == 0:
            reserve_in: int = self.reserve0
            reserve_out: int = self.reserve1
        else:
            reserve_in = self.reserve1
            reserve_out = self.reserve0
        
        # 计算输出使用整数运算
        amount_in_with_fee: int = amount_in * self.FEE_NUMERATOR
        numerator: int = amount_in_with_fee * reserve_out
        denominator: int = reserve_in * self.FEE_DENOMINATOR + amount_in_with_fee
        
        if denominator <= 0:
            raise AssertionError("计算分母错误")
            
        amount_out: int = numerator // denominator
        
        if amount_out <= 0:
            raise AssertionError("输出金额太小")
        if amount_out >= reserve_out:
            raise AssertionError("输出超出储备量")
        
        # 更新储备
        if token_in == 0:
            self.reserve0 += amount_in
            self.reserve1 -= amount_out
        else:
            self.reserve1 += amount_in
            self.reserve0 -= amount_out
            
        return amount_out

    def get_amount_out(self, token_in: int, amount_in: int) -> int:
        """
        计算给定输入能获得的输出数量 (不执行交易)
        
        参数:
        - token_in: 输入代币类型 (0 或 1)
        - amount_in: 输入代币数量
        
        返回: 预期输出代币数量
        """
        # 输入验证
        if not isinstance(token_in, int) or token_in not in [0, 1]:
            raise TypeError("token_in必须是0或1")
        if not isinstance(amount_in, int):
            raise TypeError("输入金额必须是整数")
            
        if amount_in <= 0:
            raise AssertionError("输入数量必须大于0")
        if self.reserve0 <= 0 or self.reserve1 <= 0:
            raise AssertionError("池未初始化")
        
        if token_in == 0:
            reserve_in: int = self.reserve0
            reserve_out: int = self.reserve1
        else:
            reserve_in = self.reserve1
            reserve_out = self.reserve0
            
        # 与swap函数完全一致的计算
        amount_in_with_fee: int = amount_in * self.FEE_NUMERATOR
        numerator: int = amount_in_with_fee * reserve_out
        denominator: int = reserve_in * self.FEE_DENOMINATOR + amount_in_with_fee
        
        if denominator <= 0:
            raise AssertionError("计算分母错误")
            
        amount_out: int = numerator // denominator
        
        if amount_out <= 0:
            raise AssertionError("输出金额太小")
        if amount_out >= reserve_out:
            raise AssertionError("输入过大，超出池容量")
        
        return amount_out

    def get_amount_in(self, token_out: int, amount_out: int) -> int:
        """
        计算获得指定输出需要的输入数量 (不执行交易)
        
        参数:
        - token_out: 输出代币类型 (0 或 1)
        - amount_out: 期望输出代币数量
        
        返回: 需要输入的代币数量
        """
        # 输入验证
        if not isinstance(token_out, int) or token_out not in [0, 1]:
            raise TypeError("token_out必须是0或1")
        if not isinstance(amount_out, int):
            raise TypeError("输出金额必须是整数")
            
        if amount_out <= 0:
            raise AssertionError("输出数量必须大于0")
        if self.reserve0 <= 0 or self.reserve1 <= 0:
            raise AssertionError("池未初始化")
        
        if token_out == 0:
            reserve_out: int = self.reserve0
            reserve_in: int = self.reserve1
        else:
            reserve_out = self.reserve1
            reserve_in = self.reserve0
            
        if amount_out >= reserve_out:
            raise AssertionError("期望输出超出储备")
        
        # 反向计算公式
        numerator: int = amount_out * reserve_in * self.FEE_DENOMINATOR
        denominator: int = (reserve_out - amount_out) * self.FEE_NUMERATOR
        
        if denominator <= 0:
            raise AssertionError("计算分母错误")
            
        # 向上取整
        amount_in: int = (numerator + denominator - 1) // denominator
        
        return amount_in

    def get_price(self, token: int) -> float:
        """
        获取代币价格
        
        参数:
        - token: 要查询价格的代币 (0 或 1)
        
        返回: 代币价格
        """
        if not isinstance(token, int) or token not in [0, 1]:
            raise TypeError("token必须是0或1")
            
        if token == 0:
            return float(self.reserve1) / float(self.reserve0) if self.reserve0 > 0 else 0.0
        else:
            return float(self.reserve0) / float(self.reserve1) if self.reserve1 > 0 else 0.0

    def get_k_value(self) -> int:
        """
        获取恒定乘积值 k
        
        返回: k值
        """
        return self.reserve0 * self.reserve1

    def get_liquidity_info(self, provider: str) -> Tuple[int, int, int]:
        """
        获取流动性提供者信息
        
        参数:
        - provider: 流动性提供者地址
        
        返回: (liquidity_shares, token0_value, token1_value)
        """
        if not isinstance(provider, str):
            raise TypeError("提供者地址必须是字符串")
            
        liquidity: int = self.liquidity_providers.get(provider, 0)
        if self.total_liquidity <= 0:
            return 0, 0, 0
        
        token0_value: int = (liquidity * self.reserve0) // self.total_liquidity
        token1_value: int = (liquidity * self.reserve1) // self.total_liquidity
        
        return liquidity, token0_value, token1_value

    def verify_k_invariant(self, old_k: int, tolerance: float = 0.000001) -> bool:
        """
        验证K值不变性
        
        参数:
        - old_k: 旧的k值
        - tolerance: 容忍度
        
        返回: 是否通过验证
        """
        if not isinstance(old_k, int):
            raise TypeError("old_k必须是整数")
        if not isinstance(tolerance, (int, float)):
            raise TypeError("tolerance必须是数字")
            
        new_k: int = self.get_k_value()
        return new_k >= old_k * (1.0 - tolerance)

    def safe_swap_with_slippage(self, token_in: int, amount_in: int, min_amount_out: int) -> int:
        """
        带滑点保护的安全交换
        
        参数:
        - token_in: 输入代币类型 (0 或 1)
        - amount_in: 输入代币数量
        - min_amount_out: 最小输出要求
        
        返回: 实际输出数量
        """
        if not isinstance(min_amount_out, int):
            raise TypeError("min_amount_out必须是整数")
            
        # 预测输出
        predicted_out: int = self.get_amount_out(token_in, amount_in)
        if predicted_out < min_amount_out:
            raise AssertionError("滑点过大: 预期{}, 最小要求{}".format(predicted_out, min_amount_out))
        
        # 记录旧k值
        old_k: int = self.get_k_value()
        
        # 执行交换
        actual_out: int = self.swap(token_in, amount_in)
        
        # 验证结果
        if not self.verify_k_invariant(old_k):
            raise AssertionError("K值不变性验证失败")
        if actual_out < min_amount_out:
            raise AssertionError("实际输出低于最小要求")
        
        return actual_out

    def get_pool_info(self) -> Dict[str, Union[int, float]]:
        """
        获取池子详细信息
        
        返回: 池子状态字典
        """
        provider_count: int = len([p for p in self.liquidity_providers.keys() if p != 'LOCKED'])
        
        return {
            'reserve0': self.reserve0,
            'reserve1': self.reserve1,
            'total_liquidity': self.total_liquidity,
            'k_value': self.get_k_value(),
            'price_token0': self.get_price(0),
            'price_token1': self.get_price(1),
            'locked_liquidity': self.liquidity_providers.get('LOCKED', 0),
            'provider_count': provider_count
        }

    def calculate_slippage(self, token_in: int, amount_in: int) -> float:
        """
        计算交易滑点
        
        参数:
        - token_in: 输入代币类型 (0 或 1)
        - amount_in: 输入代币数量
        
        返回: 滑点百分比
        """
        if not isinstance(token_in, int) or token_in not in [0, 1]:
            raise TypeError("token_in必须是0或1")
        if not isinstance(amount_in, int):
            raise TypeError("amount_in必须是整数")
            
        # 当前价格
        current_price: float = self.get_price(token_in)
        
        # 预期输出
        amount_out: int = self.get_amount_out(token_in, amount_in)
        
        # 实际兑换率
        actual_rate: float = float(amount_out) / float(amount_in)
        
        # 计算滑点
        slippage: float = ((current_price - actual_rate) / current_price) * 100.0
        
        return slippage

    def estimate_gas_cost(self, operation: str) -> int:
        """
        估算Gas消耗 (模拟)
        
        参数:
        - operation: 操作类型 ('swap', 'add_liquidity', 'remove_liquidity')
        
        返回: 估算的Gas消耗
        """
        if not isinstance(operation, str):
            raise TypeError("operation必须是字符串")
            
        gas_costs: Dict[str, int] = {
            'swap': 100000,
            'add_liquidity': 150000,
            'remove_liquidity': 120000,
            'initialize': 200000
        }
        
        return gas_costs.get(operation, 100000)


# 测试代码 - 验证类型注解
def run_type_annotation_tests() -> None:
    """运行类型注解测试"""
    print("=== 类型注解功能测试 ===")
    
    try:
        # 创建池实例
        pool: UniswapV2Pool = UniswapV2Pool()
        
        # 测试1: 初始化
        print("\n1. 初始化测试")
        user_liquidity: int = pool.initialize_pool(10000, 20000, 'Alice')
        print("用户流动性: {} (类型: {})".format(user_liquidity, type(user_liquidity).__name__))
        
        # 测试2: 添加流动性
        print("\n2. 添加流动性测试")
        result: Tuple[int, int, int, int, int] = pool.add_liquidity(5000, 8000, 'Bob')
        liquidity, used0, used1, refund0, refund1 = result
        print("返回类型: {}".format(type(result).__name__))
        print("各项值: liquidity={}, used0={}, used1={}, refund0={}, refund1={}".format(
            liquidity, used0, used1, refund0, refund1))
        
        # 测试3: 价格查询
        print("\n3. 价格查询测试")
        price0: float = pool.get_price(0)
        price1: float = pool.get_price(1)
        print("Token0价格: {} (类型: {})".format(price0, type(price0).__name__))
        print("Token1价格: {} (类型: {})".format(price1, type(price1).__name__))
        
        # 测试4: 交换
        print("\n4. 交换测试")
        amount_out: int = pool.swap(0, 1000)
        print("输出数量: {} (类型: {})".format(amount_out, type(amount_out).__name__))
        
        # 测试5: 池信息
        print("\n5. 池信息测试")
        info: Dict[str, Union[int, float]] = pool.get_pool_info()
        print("池信息类型: {}".format(type(info).__name__))
        for key, value in info.items():
            print("  {}: {} (类型: {})".format(key, value, type(value).__name__))
        
        # 测试6: 滑点计算
        print("\n6. 滑点计算测试")
        slippage: float = pool.calculate_slippage(1, 2000)
        print("滑点: {:.4f}% (类型: {})".format(slippage, type(slippage).__name__))
        
        # 测试7: Gas估算
        print("\n7. Gas估算测试")
        gas_cost: int = pool.estimate_gas_cost('swap')
        print("Gas消耗: {} (类型: {})".format(gas_cost, type(gas_cost).__name__))
        
        print("\n✅ 所有类型注解测试通过！")
        
    except Exception as e:
        print("❌ 测试失败: {}".format(str(e)))
        import traceback
        traceback.print_exc()


def main() -> None:
    """主函数"""
    print("=== Uniswap V2 Pool - 完整类型注解版本测试 ===")
    run_type_annotation_tests()


if __name__ == "__main__":
    main()