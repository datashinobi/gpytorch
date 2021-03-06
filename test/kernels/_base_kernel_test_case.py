#!/usr/bin/env python3

from abc import abstractmethod
import torch


class BaseKernelTestCase(object):
    @abstractmethod
    def create_kernel_no_ard(self, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def create_kernel_ard(self, num_dims, **kwargs):
        raise NotImplementedError()

    def test_active_dims_list(self):
        kernel = self.create_kernel_no_ard(active_dims=[0, 2, 4, 6])
        x = torch.randn(50, 10)
        covar_mat = kernel(x).evaluate_kernel().evaluate()
        kernel_basic = self.create_kernel_no_ard()
        covar_mat_actual = kernel_basic(x[:, [0, 2, 4, 6]]).evaluate_kernel().evaluate()

        self.assertLess(torch.norm(covar_mat - covar_mat_actual), 1e-4)

    def test_active_dims_range(self):
        active_dims = list(range(3, 9))
        kernel = self.create_kernel_no_ard(active_dims=active_dims)
        x = torch.randn(50, 10)
        covar_mat = kernel(x).evaluate_kernel().evaluate()
        kernel_basic = self.create_kernel_no_ard()
        covar_mat_actual = kernel_basic(x[:, active_dims]).evaluate_kernel().evaluate()

        self.assertLess(torch.norm(covar_mat - covar_mat_actual), 1e-4)

    def test_no_batch_kernel_single_batch_x_no_ard(self):
        kernel = self.create_kernel_no_ard()
        x = torch.randn(2, 50, 2)
        batch_covar_mat = kernel(x).evaluate_kernel().evaluate()

        actual_mat_1 = kernel(x[0]).evaluate_kernel().evaluate()
        actual_mat_2 = kernel(x[1]).evaluate_kernel().evaluate()
        actual_covar_mat = torch.cat([actual_mat_1.unsqueeze(0), actual_mat_2.unsqueeze(0)])

        self.assertLess(torch.norm(batch_covar_mat - actual_covar_mat), 1e-4)

    def test_single_batch_kernel_single_batch_x_no_ard(self):
        kernel = self.create_kernel_no_ard(batch_shape=torch.Size([]))
        x = torch.randn(2, 50, 2)
        batch_covar_mat = kernel(x).evaluate_kernel().evaluate()

        actual_mat_1 = kernel(x[0]).evaluate_kernel().evaluate()
        actual_mat_2 = kernel(x[1]).evaluate_kernel().evaluate()
        actual_covar_mat = torch.cat([actual_mat_1.unsqueeze(0), actual_mat_2.unsqueeze(0)])

        self.assertLess(torch.norm(batch_covar_mat - actual_covar_mat), 1e-4)

    def test_no_batch_kernel_double_batch_x_no_ard(self):
        kernel = self.create_kernel_no_ard(batch_shape=torch.Size([]))
        x = torch.randn(3, 2, 50, 2)
        batch_covar_mat = kernel(x).evaluate_kernel().evaluate()

        ij_actual_covars = []
        for i in range(x.size(0)):
            i_actual_covars = []
            for j in range(x.size(1)):
                i_actual_covars.append(kernel(x[i, j]).evaluate_kernel().evaluate())
            ij_actual_covars.append(torch.cat([ac.unsqueeze(0) for ac in i_actual_covars]))

        actual_covar_mat = torch.cat([ac.unsqueeze(0) for ac in ij_actual_covars])

        self.assertLess(torch.norm(batch_covar_mat - actual_covar_mat), 1e-4)

    def test_no_batch_kernel_double_batch_x_ard(self):
        try:
            kernel = self.create_kernel_ard(num_dims=2, batch_shape=torch.Size([]))
        except NotImplementedError:
            return

        x = torch.randn(3, 2, 50, 2)
        batch_covar_mat = kernel(x).evaluate_kernel().evaluate()

        ij_actual_covars = []
        for i in range(x.size(0)):
            i_actual_covars = []
            for j in range(x.size(1)):
                i_actual_covars.append(kernel(x[i, j]).evaluate_kernel().evaluate())
            ij_actual_covars.append(torch.cat([ac.unsqueeze(0) for ac in i_actual_covars]))

        actual_covar_mat = torch.cat([ac.unsqueeze(0) for ac in ij_actual_covars])

        self.assertLess(torch.norm(batch_covar_mat - actual_covar_mat), 1e-4)

    def test_smoke_double_batch_kernel_double_batch_x_no_ard(self):
        kernel = self.create_kernel_no_ard(batch_shape=torch.Size([3, 2]))
        x = torch.randn(3, 2, 50, 2)
        batch_covar_mat = kernel(x).evaluate_kernel().evaluate()
        return batch_covar_mat

    def test_smoke_double_batch_kernel_double_batch_x_ard(self):
        try:
            kernel = self.create_kernel_ard(num_dims=2, batch_shape=torch.Size([3, 2]))
        except NotImplementedError:
            return

        x = torch.randn(3, 2, 50, 2)
        batch_covar_mat = kernel(x).evaluate_kernel().evaluate()
        return batch_covar_mat
