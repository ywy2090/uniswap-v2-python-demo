# -*- coding: utf-8 -*-
"""
Uniswap V2 AMM Pool Implementation - Python 3 Compatible Version
兼容Python 3.6+的Uniswap V2自动做市商实现
"""

class UniswapV2Pool:
    """
    Uniswap V2 自动做市商(AMM)流动性池实现 - Python 3兼容版本
    基于恒定乘积公式: x * y = k
    """
    
    def __init__(self):
        """初始化流动性池"""
        self.reserve0 = 0  # 代币0的储备量
        self.reserve1 = 0  # 代币1的储备量
        self.total_liquidity = 0  # 流动性池的总流动性份额
        self.liquidity_providers = {}  # 记录流动性提供者及其对应的流动性份额
        self.MINIMUM_LIQUIDITY = 1000  # 最小流动性锁定，防止恶意操作
        self.FEE_DENOMINATOR = 1000  # 手续费分母
        self.FEE_NUMERATOR = 997  # 手续费分子 (1000-3 = 997, 表示0.3%手续费)

    def initialize_pool(self, amount0, amount1, provider):
        """
        初始化流动性池
        
        功能: 为空的流动性池提供初始流动性，建立两种代币的初始比例
        AMM公式依据:
        - 初始流动性计算: L = sqrt(x * y)
        - 建立初始恒定乘积: k = x * y
        
        参数:
        - amount0: 代币0的初始投入量 (int)
        - amount1: 代币1的初始投入量 (int)
        - provider: 流动性提供者地址 (str)
        
        返回: 用户获得的流动性份额 (int)
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
        liquidity_squared = amount0 * amount1
        if liquidity_squared < self.MINIMUM_LIQUIDITY * self.MINIMUM_LIQUIDITY:
            raise AssertionError("初始流动性太小，至少需要 {}".format(self.MINIMUM_LIQUIDITY))
        
        # 使用整数平方根避免浮点数问题
        liquidity = int(liquidity_squared ** 0.5)
        if liquidity <= self.MINIMUM_LIQUIDITY:
            raise AssertionError("流动性计算结果太小")
        
        # 设置储备
        self.reserve0 = amount0
        self.reserve1 = amount1
        
        # 锁定最小流动性，给特殊地址（永久锁定）
        self.total_liquidity = liquidity
        user_liquidity = liquidity - self.MINIMUM_LIQUIDITY
        
        self.liquidity_providers['LOCKED'] = self.MINIMUM_LIQUIDITY
        self.liquidity_providers[provider] = user_liquidity
        
        return user_liquidity

    def add_liquidity(self, amount0, amount1, provider):
        """
        增加流动性
        
        功能: 向现有流动性池添加流动性，取较小的份额比例，多余代币退还
        
        参数:
        - amount0: 用户提供的代币0数量 (int)
        - amount1: 用户提供的代币1数量 (int)
        - provider: 流动性提供者地址 (str)
        
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
        # share0 = amount0 / self.reserve0 * self.total_liquidity
        share0 = (amount0 * self.total_liquidity) // self.reserve0
        share1 = (amount1 * self.total_liquidity) // self.reserve1
        
        # 取较小份额
        min_share = min(share0, share1)
        if min_share <= 0:
            raise AssertionError("流动性太小，无法添加")
        
        # 根据较小份额计算实际使用金额
        actual_amount0 = (min_share * self.reserve0) // self.total_liquidity
        actual_amount1 = (min_share * self.reserve1) // self.total_liquidity
        
        # 计算退还金额
        refund0 = amount0 - actual_amount0
        refund1 = amount1 - actual_amount1
        
        # 更新状态
        liquidity = min_share
        self.reserve0 += actual_amount0
        self.reserve1 += actual_amount1
        self.total_liquidity += liquidity
        
        if provider not in self.liquidity_providers:
            self.liquidity_providers[provider] = 0
        self.liquidity_providers[provider] += liquidity
        
        return liquidity, actual_amount0, actual_amount1, refund0, refund1

    def remove_liquidity(self, liquidity, provider):
        """
        移除流动性
        
        功能: 从流动性池中移除指定份额的流动性，按比例取回两种代币
        
        参数:
        - liquidity: 要移除的流动性份额 (int)
        - provider: 流动性提供者地址 (str)
        
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
        
        provider_liquidity = self.liquidity_providers.get(provider, 0)
        if provider_liquidity < liquidity:
            raise AssertionError("流动性份额不足")
        
        # 确保移除后仍有足够的总流动性
        remaining_liquidity = self.total_liquidity - liquidity
        if remaining_liquidity < self.MINIMUM_LIQUIDITY:
            raise AssertionError("不能移除过多流动性，必须保留最小流动性")
        
        # 计算取回金额
        amount0 = (liquidity * self.reserve0) // self.total_liquidity
        amount1 = (liquidity * self.reserve1) // self.total_liquidity
        
        # 更新状态
        self.reserve0 -= amount0
        self.reserve1 -= amount1
        self.total_liquidity -= liquidity
        self.liquidity_providers[provider] -= liquidity
        
        return amount0, amount1

    def swap(self, token_in, amount_in):
        """
        代币交换
        
        功能: 使用恒定乘积公式进行代币交换，正确处理交易手续费
        
        参数:
        - token_in: 输入代币类型 (int: 0 或 1)
        - amount_in: 输入代币数量 (int)
        
        返回: 输出代币数量 (int)
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
            reserve_in, reserve_out = self.reserve0, self.reserve1
        else:
            reserve_in, reserve_out = self.reserve1, self.reserve0
        
        # 计算输出使用整数运算
        # amount_out = (amount_in * 997 * reserve_out) / (reserve_in * 1000 + amount_in * 997)
        amount_in_with_fee = amount_in * self.FEE_NUMERATOR
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in * self.FEE_DENOMINATOR + amount_in_with_fee
        
        if denominator <= 0:
            raise AssertionError("计算分母错误")
            
        amount_out = numerator // denominator
        
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

    def get_amount_out(self, token_in, amount_in):
        """
        计算给定输入能获得的输出数量 (不执行交易)
        
        参数:
        - token_in: 输入代币类型 (int: 0 或 1)
        - amount_in: 输入代币数量 (int)
        
        返回: 预期输出代币数量 (int)
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
            reserve_in, reserve_out = self.reserve0, self.reserve1
        else:
            reserve_in, reserve_out = self.reserve1, self.reserve0
            
        # 与swap函数完全一致的计算
        amount_in_with_fee = amount_in * self.FEE_NUMERATOR
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in * self.FEE_DENOMINATOR + amount_in_with_fee
        
        if denominator <= 0:
            raise AssertionError("计算分母错误")
            
        amount_out = numerator // denominator
        
        if amount_out <= 0:
            raise AssertionError("输出金额太小")
        if amount_out >= reserve_out:
            raise AssertionError("输入过大，超出池容量")
        
        return amount_out

    def get_amount_in(self, token_out, amount_out):
        """
        计算获得指定输出需要的输入数量 (不执行交易)
        
        参数:
        - token_out: 输出代币类型 (int: 0 或 1)
        - amount_out: 期望输出代币数量 (int)
        
        返回: 需要输入的代币数量 (int)
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
            reserve_out, reserve_in = self.reserve0, self.reserve1
        else:
            reserve_out, reserve_in = self.reserve1, self.reserve0
            
        if amount_out >= reserve_out:
            raise AssertionError("期望输出超出储备")
        
        # 反向计算公式
        # amount_in = (amount_out * reserve_in * 1000) / ((reserve_out - amount_out) * 997)
        numerator = amount_out * reserve_in * self.FEE_DENOMINATOR
        denominator = (reserve_out - amount_out) * self.FEE_NUMERATOR
        
        if denominator <= 0:
            raise AssertionError("计算分母错误")
            
        # 向上取整
        amount_in = (numerator + denominator - 1) // denominator
        
        return amount_in

    def get_price(self, token):
        """
        获取代币价格
        
        参数:
        - token: 要查询价格的代币 (int: 0 或 1)
        
        返回: 代币价格 (float)
        """
        if not isinstance(token, int) or token not in [0, 1]:
            raise TypeError("token必须是0或1")
            
        if token == 0:
            return float(self.reserve1) / float(self.reserve0) if self.reserve0 > 0 else 0.0
        else:
            return float(self.reserve0) / float(self.reserve1) if self.reserve1 > 0 else 0.0

    def get_k_value(self):
        """
        获取恒定乘积值 k
        
        返回: k值 (int)
        """
        return self.reserve0 * self.reserve1

    def get_liquidity_info(self, provider):
        """
        获取流动性提供者信息
        
        参数:
        - provider: 流动性提供者地址 (str)
        
        返回: (liquidity_shares, token0_value, token1_value)
        """
        if not isinstance(provider, str):
            raise TypeError("提供者地址必须是字符串")
            
        liquidity = self.liquidity_providers.get(provider, 0)
        if self.total_liquidity <= 0:
            return 0, 0, 0
        
        token0_value = (liquidity * self.reserve0) // self.total_liquidity
        token1_value = (liquidity * self.reserve1) // self.total_liquidity
        
        return liquidity, token0_value, token1_value

    def verify_k_invariant(self, old_k, tolerance=0.000001):
        """
        验证K值不变性
        
        参数:
        - old_k: 旧的k值 (int)
        - tolerance: 容忍度 (float)
        
        返回: 是否通过验证 (bool)
        """
        new_k = self.get_k_value()
        return new_k >= old_k * (1.0 - tolerance)

    def safe_swap_with_slippage(self, token_in, amount_in, min_amount_out):
        """
        带滑点保护的安全交换
        
        参数:
        - token_in: 输入代币类型 (int: 0 或 1)
        - amount_in: 输入代币数量 (int)
        - min_amount_out: 最小输出要求 (int)
        
        返回: 实际输出数量 (int)
        """
        # 预测输出
        predicted_out = self.get_amount_out(token_in, amount_in)
        if predicted_out < min_amount_out:
            raise AssertionError("滑点过大: 预期{}, 最小要求{}".format(predicted_out, min_amount_out))
        
        # 记录旧k值
        old_k = self.get_k_value()
        
        # 执行交换
        actual_out = self.swap(token_in, amount_in)
        
        # 验证结果
        if not self.verify_k_invariant(old_k):
            raise AssertionError("K值不变性验证失败")
        if actual_out < min_amount_out:
            raise AssertionError("实际输出低于最小要求")
        
        return actual_out

    def get_pool_info(self):
        """
        获取池子详细信息
        
        返回: 池子状态字典
        """
        return {
            'reserve0': self.reserve0,
            'reserve1': self.reserve1,
            'total_liquidity': self.total_liquidity,
            'k_value': self.get_k_value(),
            'price_token0': self.get_price(0),
            'price_token1': self.get_price(1),
            'locked_liquidity': self.liquidity_providers.get('LOCKED', 0),
            'provider_count': len([p for p in self.liquidity_providers.keys() if p != 'LOCKED'])
        }


# 测试代码 - 验证Python 3兼容性
def main():
    """主测试函数"""
    print("=== Uniswap V2 Pool Python 3 兼容性测试 ===")
    
    try:
        # 测试1: 基本功能测试
        print("\n1. 基本功能测试")
        pool = UniswapV2Pool()
        
        # 初始化池
        user_liquidity = pool.initialize_pool(10000, 20000, 'Alice')
        print("初始化成功，Alice获得流动性: {}".format(user_liquidity))
        
        # 获取池信息
        info = pool.get_pool_info()
        print("池信息: {}".format(info))
        
        # 测试2: 添加流动性
        print("\n2. 添加流动性测试")
        liquidity, used0, used1, refund0, refund1 = pool.add_liquidity(5000, 8000, 'Bob')
        print("Bob添加流动性:")
        print("  获得流动性: {}".format(liquidity))
        print("  使用代币: {} Token0, {} Token1".format(used0, used1))
        print("  退还代币: {} Token0, {} Token1".format(refund0, refund1))
        
        # 测试3: 交换功能
        print("\n3. 交换功能测试")
        amount_in = 1000
        predicted_out = pool.get_amount_out(0, amount_in)
        actual_out = pool.swap(0, amount_in)
        
        print("交换 {} Token0:".format(amount_in))
        print("  预测输出: {} Token1".format(predicted_out))
        print("  实际输出: {} Token1".format(actual_out))
        print("  计算误差: {}".format(abs(predicted_out - actual_out)))
        
        # 测试4: 反向计算
        print("\n4. 反向计算测试")
        target_out = 500
        needed_in = pool.get_amount_in(1, target_out)
        verify_out = pool.get_amount_out(0, needed_in)
        
        print("获得 {} Token1:".format(target_out))
        print("  需要输入: {} Token0".format(needed_in))
        print("  验证输出: {} Token1".format(verify_out))
        print("  反向误差: {}".format(abs(target_out - verify_out)))
        
        # 测试5: 滑点保护
        print("\n5. 滑点保护测试")
        try:
            safe_out = pool.safe_swap_with_slippage(1, 2000, 800)
            print("滑点保护交换成功，输出: {}".format(safe_out))
        except AssertionError as e:
            print("滑点保护生效: {}".format(str(e)))
        
        # 测试6: 移除流动性
        print("\n6. 移除流动性测试")
        alice_liquidity, alice_token0, alice_token1 = pool.get_liquidity_info('Alice')
        print("Alice当前流动性: {}".format(alice_liquidity))
        
        # 移除一半流动性
        remove_amount = alice_liquidity // 2
        amount0, amount1 = pool.remove_liquidity(remove_amount, 'Alice')
        print("移除 {} 流动性份额:".format(remove_amount))
        print("  取回: {} Token0, {} Token1".format(amount0, amount1))
        
        # 最终状态
        print("\n=== 最终池状态 ===")
        final_info = pool.get_pool_info()
        for key, value in final_info.items():
            if isinstance(value, float):
                print("{}: {:.6f}".format(key, value))
            else:
                print("{}: {}".format(key, value))
        
        print("\n✅ 所有测试通过！Python 3兼容性验证成功")
        
    except Exception as e:
        print("❌ 测试失败: {}".format(str(e)))
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()