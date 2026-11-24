// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {Biblioteca} from "../src/Biblioteca.sol";

contract BibliotecaTest is Test {
    Biblioteca biblioteca;

    address bibliotecaria = makeAddr("bibliotecaria");
    address leitora = makeAddr("leitora");
    address leitor = makeAddr("leitor");
    address intruso = makeAddr("intruso");

    uint256 domCasmurro;

    function setUp() public {
        biblioteca = new Biblioteca();
        biblioteca.definirBibliotecario(bibliotecaria, true);
        vm.prank(bibliotecaria);
        domCasmurro = biblioteca.cadastrarLivro("Dom Casmurro", 2);
    }

    function emprestarComo(address quem, uint256 livroId, address para) internal {
        vm.prank(quem);
        biblioteca.emprestar(livroId, para);
    }

    function test_construtorTornaImplantadorDonoEBibliotecario() public view {
        assertEq(biblioteca.dono(), address(this));
        assertTrue(biblioteca.bibliotecario(address(this)));
        assertTrue(biblioteca.bibliotecario(bibliotecaria));
        assertFalse(biblioteca.bibliotecario(intruso));
    }

    function test_cadastrarLivroGuardaEstadoEEmiteEvento() public {
        vm.expectEmit(true, false, false, true, address(biblioteca));
        emit Biblioteca.LivroCadastrado(2, "Memorias Postumas", 1);

        vm.prank(bibliotecaria);
        uint256 id = biblioteca.cadastrarLivro("Memorias Postumas", 1);

        (string memory titulo, uint32 exemplares, uint32 disponiveis) = biblioteca.consultarLivro(id);
        assertEq(id, 2);
        assertEq(biblioteca.totalLivros(), 2);
        assertEq(titulo, "Memorias Postumas");
        assertEq(exemplares, 1);
        assertEq(disponiveis, 1);
    }

    function test_emprestarReservaExemplarEEmiteEvento() public {
        uint64 vencimentoEsperado = uint64(block.timestamp) + biblioteca.prazoEmprestimo();

        vm.expectEmit(true, true, false, true, address(biblioteca));
        emit Biblioteca.LivroEmprestado(domCasmurro, leitora, vencimentoEsperado);
        emprestarComo(bibliotecaria, domCasmurro, leitora);

        (, , uint32 disponiveis) = biblioteca.consultarLivro(domCasmurro);
        (bool ativo, uint64 vencimento, bool renovado, uint64 atraso) =
            biblioteca.consultarEmprestimo(domCasmurro, leitora);
        assertEq(disponiveis, 1);
        assertEq(biblioteca.emprestimosAtivos(leitora), 1);
        assertTrue(ativo);
        assertEq(vencimento, vencimentoEsperado);
        assertFalse(renovado);
        assertEq(atraso, 0);
    }

    function test_devolverNoPrazoLiberaExemplarSemAtraso() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);
        vm.warp(block.timestamp + 10 days);

        vm.expectEmit(true, true, false, true, address(biblioteca));
        emit Biblioteca.LivroDevolvido(domCasmurro, leitora, 0);
        vm.prank(bibliotecaria);
        biblioteca.devolver(domCasmurro, leitora);

        (, , uint32 disponiveis) = biblioteca.consultarLivro(domCasmurro);
        (bool ativo, , , ) = biblioteca.consultarEmprestimo(domCasmurro, leitora);
        assertEq(disponiveis, 2);
        assertEq(biblioteca.emprestimosAtivos(leitora), 0);
        assertFalse(ativo);
    }

    function test_devolverComAtrasoInformaDiasNoEvento() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);
        vm.warp(block.timestamp + 14 days + 3 days + 1);

        vm.expectEmit(true, true, false, true, address(biblioteca));
        emit Biblioteca.LivroDevolvido(domCasmurro, leitora, 4);
        vm.prank(bibliotecaria);
        biblioteca.devolver(domCasmurro, leitora);
    }

    function test_consultarEmprestimoMostraAtrasoSemTransacao() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);
        vm.warp(block.timestamp + 16 days);

        (bool ativo, , , uint64 atraso) = biblioteca.consultarEmprestimo(domCasmurro, leitora);
        assertTrue(ativo);
        assertEq(atraso, 2);
    }

    function test_leitorRenovaOProprioEmprestimoUmaVez() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);
        (, uint64 vencimentoOriginal, , ) = biblioteca.consultarEmprestimo(domCasmurro, leitora);
        uint64 novoVencimento = vencimentoOriginal + biblioteca.prazoEmprestimo();

        vm.expectEmit(true, true, false, true, address(biblioteca));
        emit Biblioteca.EmprestimoRenovado(domCasmurro, leitora, novoVencimento);
        vm.prank(leitora);
        biblioteca.renovar(domCasmurro);

        (, uint64 vencimento, bool renovado, ) = biblioteca.consultarEmprestimo(domCasmurro, leitora);
        assertEq(vencimento, novoVencimento);
        assertTrue(renovado);
    }

    function test_transferenciaDeDonoExigeAceite() public {
        biblioteca.transferirDono(bibliotecaria);
        assertEq(biblioteca.dono(), address(this));
        assertEq(biblioteca.donoPendente(), bibliotecaria);

        vm.expectEmit(true, true, false, false, address(biblioteca));
        emit Biblioteca.DonoAlterado(address(this), bibliotecaria);
        vm.prank(bibliotecaria);
        biblioteca.aceitarDono();

        assertEq(biblioteca.dono(), bibliotecaria);
        assertEq(biblioteca.donoPendente(), address(0));
        vm.expectRevert(abi.encodeWithSelector(Biblioteca.SomenteDono.selector, address(this)));
        biblioteca.definirBibliotecario(intruso, true);
    }

    function test_revertQuandoIntrusoCadastraLivro() public {
        vm.expectRevert(abi.encodeWithSelector(Biblioteca.SomenteBibliotecario.selector, intruso));
        vm.prank(intruso);
        biblioteca.cadastrarLivro("Livro Falso", 100);
    }

    function test_revertQuandoIntrusoRegistraDevolucaoFalsa() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.SomenteBibliotecario.selector, leitora));
        vm.prank(leitora);
        biblioteca.devolver(domCasmurro, leitora);

        (bool ativo, , , ) = biblioteca.consultarEmprestimo(domCasmurro, leitora);
        assertTrue(ativo);
    }

    function test_revertQuandoNaoDonoTentaSePromover() public {
        vm.expectRevert(abi.encodeWithSelector(Biblioteca.SomenteDono.selector, bibliotecaria));
        vm.prank(bibliotecaria);
        biblioteca.definirBibliotecario(intruso, true);
        assertFalse(biblioteca.bibliotecario(intruso));
    }

    function test_revertQuandoBibliotecarioRevogadoTentaEmprestar() public {
        biblioteca.definirBibliotecario(bibliotecaria, false);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.SomenteBibliotecario.selector, bibliotecaria));
        emprestarComo(bibliotecaria, domCasmurro, leitora);
    }

    function test_revertQuandoTerceiroAceitaDono() public {
        biblioteca.transferirDono(bibliotecaria);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.SomenteDonoPendente.selector, intruso));
        vm.prank(intruso);
        biblioteca.aceitarDono();
    }

    function test_revertComTituloVazioOuLongoDemais() public {
        vm.startPrank(bibliotecaria);
        vm.expectRevert(Biblioteca.TituloInvalido.selector);
        biblioteca.cadastrarLivro("", 1);

        string memory longo = string(new bytes(biblioteca.tamanhoMaximoTitulo() + 1));
        vm.expectRevert(Biblioteca.TituloInvalido.selector);
        biblioteca.cadastrarLivro(longo, 1);
        vm.stopPrank();
    }

    function test_revertComZeroExemplares() public {
        vm.expectRevert(Biblioteca.QuantidadeInvalida.selector);
        vm.prank(bibliotecaria);
        biblioteca.cadastrarLivro("Quincas Borba", 0);
    }

    function test_revertQuandoLivroNaoExiste() public {
        vm.expectRevert(abi.encodeWithSelector(Biblioteca.LivroInexistente.selector, 99));
        emprestarComo(bibliotecaria, 99, leitora);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.LivroInexistente.selector, 99));
        biblioteca.consultarLivro(99);
    }

    function test_revertSemExemplarDisponivelNaoAlteraEstado() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);
        emprestarComo(bibliotecaria, domCasmurro, leitor);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.SemExemplarDisponivel.selector, domCasmurro));
        emprestarComo(bibliotecaria, domCasmurro, intruso);

        (, , uint32 disponiveis) = biblioteca.consultarLivro(domCasmurro);
        assertEq(disponiveis, 0);
        assertEq(biblioteca.emprestimosAtivos(intruso), 0);
    }

    function test_revertEmprestimoDuplicadoDoMesmoTitulo() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.EmprestimoDuplicado.selector, domCasmurro, leitora));
        emprestarComo(bibliotecaria, domCasmurro, leitora);
    }

    function test_revertAoPassarDoLimiteDeEmprestimos() public {
        uint256 limite = biblioteca.limitePorLeitor();
        vm.startPrank(bibliotecaria);
        for (uint256 i = 0; i < limite; i++) {
            uint256 id = biblioteca.cadastrarLivro("Volume", 1);
            biblioteca.emprestar(id, leitora);
        }
        uint256 extra = biblioteca.cadastrarLivro("Volume extra", 1);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.LimiteDeEmprestimos.selector, leitora));
        biblioteca.emprestar(extra, leitora);
        vm.stopPrank();
    }

    function test_revertDevolucaoDupla() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);
        vm.startPrank(bibliotecaria);
        biblioteca.devolver(domCasmurro, leitora);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.EmprestimoInexistente.selector, domCasmurro, leitora));
        biblioteca.devolver(domCasmurro, leitora);
        vm.stopPrank();
    }

    function test_revertRenovacaoDeEmprestimoAtrasado() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);
        vm.warp(block.timestamp + 15 days);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.EmprestimoAtrasado.selector, domCasmurro, leitora));
        vm.prank(leitora);
        biblioteca.renovar(domCasmurro);
    }

    function test_revertSegundaRenovacao() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);
        vm.startPrank(leitora);
        biblioteca.renovar(domCasmurro);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.JaRenovado.selector, domCasmurro, leitora));
        biblioteca.renovar(domCasmurro);
        vm.stopPrank();
    }

    function test_revertRenovacaoPorQuemNaoPegouOLivro() public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);

        vm.expectRevert(abi.encodeWithSelector(Biblioteca.EmprestimoInexistente.selector, domCasmurro, intruso));
        vm.prank(intruso);
        biblioteca.renovar(domCasmurro);
    }

    function testFuzz_emprestarEDevolverConservaExemplares(uint32 exemplares, uint8 quantidade) public {
        exemplares = uint32(bound(exemplares, 1, 40));
        quantidade = uint8(bound(quantidade, 0, exemplares));

        vm.startPrank(bibliotecaria);
        uint256 id = biblioteca.cadastrarLivro("Fuzz", exemplares);
        for (uint160 i = 1; i <= quantidade; i++) {
            biblioteca.emprestar(id, address(i));
        }
        (, , uint32 disponiveis) = biblioteca.consultarLivro(id);
        assertEq(disponiveis, exemplares - quantidade);

        for (uint160 i = 1; i <= quantidade; i++) {
            biblioteca.devolver(id, address(i));
        }
        vm.stopPrank();
        (, , disponiveis) = biblioteca.consultarLivro(id);
        assertEq(disponiveis, exemplares);
    }

    function testFuzz_atrasoArredondaParaCimaEmDias(uint32 segundosDepoisDoPrazo) public {
        emprestarComo(bibliotecaria, domCasmurro, leitora);
        (, uint64 vencimento, , ) = biblioteca.consultarEmprestimo(domCasmurro, leitora);
        vm.warp(vencimento + uint256(segundosDepoisDoPrazo));

        (, , , uint64 atraso) = biblioteca.consultarEmprestimo(domCasmurro, leitora);
        uint256 esperado = (uint256(segundosDepoisDoPrazo) + 1 days - 1) / 1 days;
        assertEq(atraso, esperado);
    }
}
