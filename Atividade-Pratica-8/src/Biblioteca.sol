// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Biblioteca {
    struct Livro {
        string titulo;
        uint32 exemplares;
        uint32 disponiveis;
    }

    struct Emprestimo {
        uint64 vencimento;
        bool renovado;
    }

    uint8 public constant limitePorLeitor = 3;
    uint64 public constant prazoEmprestimo = 14 days;
    uint256 public constant tamanhoMaximoTitulo = 100;

    address public dono;
    address public donoPendente;
    uint256 public totalLivros;

    mapping(address => bool) public bibliotecario;
    mapping(address => uint8) public emprestimosAtivos;
    mapping(uint256 => Livro) private livros;
    mapping(uint256 => mapping(address => Emprestimo)) private emprestimos;

    event BibliotecarioAlterado(address indexed conta, bool autorizado);
    event TransferenciaDeDonoIniciada(address indexed dono, address indexed pendente);
    event DonoAlterado(address indexed anterior, address indexed novo);
    event LivroCadastrado(uint256 indexed livroId, string titulo, uint32 exemplares);
    event LivroEmprestado(uint256 indexed livroId, address indexed leitor, uint64 vencimento);
    event EmprestimoRenovado(uint256 indexed livroId, address indexed leitor, uint64 vencimento);
    event LivroDevolvido(uint256 indexed livroId, address indexed leitor, uint64 diasAtraso);

    error SomenteDono(address chamador);
    error SomenteDonoPendente(address chamador);
    error SomenteBibliotecario(address chamador);
    error EnderecoInvalido();
    error TituloInvalido();
    error QuantidadeInvalida();
    error LivroInexistente(uint256 livroId);
    error SemExemplarDisponivel(uint256 livroId);
    error EmprestimoDuplicado(uint256 livroId, address leitor);
    error LimiteDeEmprestimos(address leitor);
    error EmprestimoInexistente(uint256 livroId, address leitor);
    error EmprestimoAtrasado(uint256 livroId, address leitor);
    error JaRenovado(uint256 livroId, address leitor);

    modifier somenteDono() {
        if (msg.sender != dono) revert SomenteDono(msg.sender);
        _;
    }

    modifier somenteBibliotecario() {
        if (!bibliotecario[msg.sender]) revert SomenteBibliotecario(msg.sender);
        _;
    }

    constructor() {
        dono = msg.sender;
        bibliotecario[msg.sender] = true;
        emit DonoAlterado(address(0), msg.sender);
        emit BibliotecarioAlterado(msg.sender, true);
    }

    function definirBibliotecario(address conta, bool autorizado) external somenteDono {
        if (conta == address(0)) revert EnderecoInvalido();
        bibliotecario[conta] = autorizado;
        emit BibliotecarioAlterado(conta, autorizado);
    }

    function transferirDono(address novoDono) external somenteDono {
        if (novoDono == address(0)) revert EnderecoInvalido();
        donoPendente = novoDono;
        emit TransferenciaDeDonoIniciada(msg.sender, novoDono);
    }

    function aceitarDono() external {
        if (msg.sender != donoPendente) revert SomenteDonoPendente(msg.sender);
        emit DonoAlterado(dono, msg.sender);
        dono = msg.sender;
        donoPendente = address(0);
    }

    function cadastrarLivro(string calldata titulo, uint32 exemplares)
        external
        somenteBibliotecario
        returns (uint256 livroId)
    {
        uint256 tamanho = bytes(titulo).length;
        if (tamanho == 0 || tamanho > tamanhoMaximoTitulo) revert TituloInvalido();
        if (exemplares == 0) revert QuantidadeInvalida();

        livroId = ++totalLivros;
        livros[livroId] = Livro(titulo, exemplares, exemplares);
        emit LivroCadastrado(livroId, titulo, exemplares);
    }

    function emprestar(uint256 livroId, address leitor) external somenteBibliotecario {
        Livro storage livro = livros[livroId];
        if (livro.exemplares == 0) revert LivroInexistente(livroId);
        if (leitor == address(0)) revert EnderecoInvalido();
        if (livro.disponiveis == 0) revert SemExemplarDisponivel(livroId);
        if (emprestimos[livroId][leitor].vencimento != 0) revert EmprestimoDuplicado(livroId, leitor);
        if (emprestimosAtivos[leitor] >= limitePorLeitor) revert LimiteDeEmprestimos(leitor);

        uint64 vencimento = uint64(block.timestamp) + prazoEmprestimo;
        livro.disponiveis -= 1;
        emprestimosAtivos[leitor] += 1;
        emprestimos[livroId][leitor] = Emprestimo(vencimento, false);
        emit LivroEmprestado(livroId, leitor, vencimento);
    }

    function renovar(uint256 livroId) external {
        Emprestimo storage emprestimo = emprestimos[livroId][msg.sender];
        if (emprestimo.vencimento == 0) revert EmprestimoInexistente(livroId, msg.sender);
        if (block.timestamp > emprestimo.vencimento) revert EmprestimoAtrasado(livroId, msg.sender);
        if (emprestimo.renovado) revert JaRenovado(livroId, msg.sender);

        emprestimo.vencimento += prazoEmprestimo;
        emprestimo.renovado = true;
        emit EmprestimoRenovado(livroId, msg.sender, emprestimo.vencimento);
    }

    function devolver(uint256 livroId, address leitor) external somenteBibliotecario {
        uint64 vencimento = emprestimos[livroId][leitor].vencimento;
        if (vencimento == 0) revert EmprestimoInexistente(livroId, leitor);

        delete emprestimos[livroId][leitor];
        livros[livroId].disponiveis += 1;
        emprestimosAtivos[leitor] -= 1;
        emit LivroDevolvido(livroId, leitor, diasDeAtraso(vencimento));
    }

    function consultarLivro(uint256 livroId)
        external
        view
        returns (string memory titulo, uint32 exemplares, uint32 disponiveis)
    {
        Livro storage livro = livros[livroId];
        if (livro.exemplares == 0) revert LivroInexistente(livroId);
        return (livro.titulo, livro.exemplares, livro.disponiveis);
    }

    function consultarEmprestimo(uint256 livroId, address leitor)
        external
        view
        returns (bool ativo, uint64 vencimento, bool renovado, uint64 diasAtraso)
    {
        Emprestimo storage emprestimo = emprestimos[livroId][leitor];
        vencimento = emprestimo.vencimento;
        ativo = vencimento != 0;
        renovado = emprestimo.renovado;
        diasAtraso = ativo ? diasDeAtraso(vencimento) : 0;
    }

    function diasDeAtraso(uint64 vencimento) private view returns (uint64) {
        if (block.timestamp <= vencimento) return 0;
        return (uint64(block.timestamp) - vencimento + 1 days - 1) / 1 days;
    }
}
