// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {Biblioteca} from "../src/Biblioteca.sol";

contract OperadorDaBiblioteca is Test {
    Biblioteca public biblioteca;
    address public bibliotecaria;
    address[] public leitores;

    uint256 public emprestimosFeitos;
    uint256 public devolucoesFeitas;

    constructor(Biblioteca alvo, address quemOpera) {
        biblioteca = alvo;
        bibliotecaria = quemOpera;
        for (uint160 i = 1; i <= 5; i++) {
            leitores.push(address(i * 1000));
        }
    }

    function totalLeitores() external view returns (uint256) {
        return leitores.length;
    }

    function cadastrar(uint32 exemplares) external {
        if (biblioteca.totalLivros() >= 6) return;
        exemplares = uint32(bound(exemplares, 1, 4));
        vm.prank(bibliotecaria);
        biblioteca.cadastrarLivro("Livro", exemplares);
    }

    function emprestar(uint256 semente, uint256 sementeLeitor) external {
        uint256 total = biblioteca.totalLivros();
        if (total == 0) return;
        uint256 livroId = bound(semente, 1, total);
        address leitor = leitores[sementeLeitor % leitores.length];

        (, , uint32 disponiveis) = biblioteca.consultarLivro(livroId);
        (bool ativo, , , ) = biblioteca.consultarEmprestimo(livroId, leitor);
        if (disponiveis == 0 || ativo) return;
        if (biblioteca.emprestimosAtivos(leitor) >= biblioteca.limitePorLeitor()) return;

        vm.prank(bibliotecaria);
        biblioteca.emprestar(livroId, leitor);
        emprestimosFeitos++;
    }

    function devolver(uint256 semente, uint256 sementeLeitor) external {
        uint256 total = biblioteca.totalLivros();
        if (total == 0) return;
        uint256 livroId = bound(semente, 1, total);
        address leitor = leitores[sementeLeitor % leitores.length];

        (bool ativo, , , ) = biblioteca.consultarEmprestimo(livroId, leitor);
        if (!ativo) return;

        vm.prank(bibliotecaria);
        biblioteca.devolver(livroId, leitor);
        devolucoesFeitas++;
    }

    function renovar(uint256 semente, uint256 sementeLeitor) external {
        uint256 total = biblioteca.totalLivros();
        if (total == 0) return;
        uint256 livroId = bound(semente, 1, total);
        address leitor = leitores[sementeLeitor % leitores.length];

        (bool ativo, uint64 vencimento, bool renovado, ) = biblioteca.consultarEmprestimo(livroId, leitor);
        if (!ativo || renovado || block.timestamp > vencimento) return;

        vm.prank(leitor);
        biblioteca.renovar(livroId);
    }

    function avancarTempo(uint32 segundos) external {
        vm.warp(block.timestamp + bound(segundos, 1 hours, 10 days));
    }
}

contract BibliotecaInvarianteTest is Test {
    Biblioteca biblioteca;
    OperadorDaBiblioteca operador;

    function setUp() public {
        address bibliotecaria = makeAddr("bibliotecaria");
        biblioteca = new Biblioteca();
        biblioteca.definirBibliotecario(bibliotecaria, true);
        operador = new OperadorDaBiblioteca(biblioteca, bibliotecaria);
        targetContract(address(operador));
    }

    function invariant_disponiveisNuncaPassamDosExemplares() public view {
        for (uint256 id = 1; id <= biblioteca.totalLivros(); id++) {
            (, uint32 exemplares, uint32 disponiveis) = biblioteca.consultarLivro(id);
            assertLe(disponiveis, exemplares);
        }
    }

    function invariant_exemplaresForaBatemComEmprestimosAtivos() public view {
        uint256 leitores = operador.totalLeitores();
        uint256 foraPorLivro;
        uint256 ativosPorLeitor;

        for (uint256 id = 1; id <= biblioteca.totalLivros(); id++) {
            (, uint32 exemplares, uint32 disponiveis) = biblioteca.consultarLivro(id);
            uint256 ativosDoLivro;
            for (uint256 i = 0; i < leitores; i++) {
                (bool ativo, , , ) = biblioteca.consultarEmprestimo(id, operador.leitores(i));
                if (ativo) ativosDoLivro++;
            }
            assertEq(exemplares - disponiveis, ativosDoLivro);
            foraPorLivro += exemplares - disponiveis;
        }

        for (uint256 i = 0; i < leitores; i++) {
            uint8 ativos = biblioteca.emprestimosAtivos(operador.leitores(i));
            assertLe(ativos, biblioteca.limitePorLeitor());
            ativosPorLeitor += ativos;
        }

        assertEq(foraPorLivro, ativosPorLeitor);
        assertEq(foraPorLivro, operador.emprestimosFeitos() - operador.devolucoesFeitas());
    }
}
